"""The ONLY module that talks to the LLM provider (Google Gemini).

Every LLM call in the backend goes through complete() /
complete_with_retry() so the provider can be swapped later without touching
orchestrator or tool logic. Gemini is accessed through its OpenAI-compatible
endpoint (generativelanguage.googleapis.com/v1beta/openai), so the request
and response shapes are the standard OpenAI chat-completions ones.

Rate limiting: Gemini's free tier allows roughly 10 requests/minute for
flash models, so a minimum spacing between consecutive calls is enforced
via LLM_MIN_INTERVAL_MS (default 6000ms - deliberately conservative; check
AI Studio and tune). A 429 is a distinct error class (RateLimitError), and
callers treat it as the single allowed retry.
"""
import asyncio
import time

import httpx

from .config import settings


class LLMError(Exception):
    pass


class RateLimitError(LLMError):
    """The provider returned HTTP 429."""


_spacing_lock = asyncio.Lock()
_last_call_monotonic = 0.0


async def _enforce_spacing() -> None:
    global _last_call_monotonic
    async with _spacing_lock:
        now = time.monotonic()
        wait_for = _last_call_monotonic + settings.min_interval_ms / 1000.0 - now
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        _last_call_monotonic = time.monotonic()


async def complete(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    json_mode: bool = False,
) -> dict:
    """One call to POST {base}/chat/completions (OpenAI-compatible)."""
    await _enforce_spacing()
    payload: dict = {
        "model": settings.llm_model,
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "max_tokens": settings.max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
    except httpx.HTTPError as e:
        raise LLMError(str(e))
    if resp.status_code == 429:
        raise RateLimitError("LLM rate limit (429)")
    if resp.status_code != 200:
        raise LLMError(f"LLM returned HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as e:
        raise LLMError(f"invalid JSON from LLM: {e}")


async def complete_with_retry(
    system_prompt: str, messages: list[dict], tools: list[dict] | None = None
) -> dict:
    """Retry budget is exactly one: a failure (including a 429) is retried
    once after the min-interval spacing; a second failure raises."""
    last_exc: Exception | None = None
    for _ in range(2):
        try:
            return await complete(system_prompt, messages, tools=tools)
        except LLMError as e:
            last_exc = e
    raise LLMError(str(last_exc))
