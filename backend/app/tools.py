"""Tool functions.

Each tool is an isolated async function: it calls llm_client with a dedicated
prompt, validates the JSON response against its pydantic schema, and returns
a plain dict. The retry budget is exactly one per tool call - a second LLM or
schema failure raises ToolFailure, which aborts the step with nothing partial
written. evaluate_analogy NEVER computes a band; the application layer does.
"""
import json
import re

from pydantic import ValidationError

from .llm_client import LLMError, complete
from .prompts import (
    ANALOGY_PROMPT,
    EVALUATE_PROMPT,
    EXTRACT_SUBCONCEPTS_PROMPT,
    FLASHCARDS_PROMPT,
    MEMES_PROMPT,
    MERMAID_PROMPT,
)
from .schemas import (
    AnalogyResult,
    EvaluateResult,
    FlashcardsResult,
    MemesResult,
    MermaidResult,
    SubConceptsResult,
)


class ToolFailure(Exception):
    """LLM call or schema validation failed twice; the step must abort."""


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of an LLM response (handles code fences and
    surrounding prose). Raises ValueError when there is no valid object."""
    if not text:
        raise ValueError("empty LLM response")
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in LLM response")
    return json.loads(text[start : end + 1])


async def _llm_json(system_prompt: str, user_prompt: str, schema) -> dict:
    """Call the LLM, validate against the schema. Exactly one retry."""
    last_exc: Exception | None = None
    for _ in range(2):
        try:
            resp = await complete(
                system_prompt,
                [{"role": "user", "content": user_prompt}],
                json_mode=True,
            )
            content = resp["choices"][0]["message"]["content"]
            return schema.model_validate(_extract_json(content)).model_dump()
        except (LLMError, ValueError, KeyError, TypeError, ValidationError) as e:
            last_exc = e
    raise ToolFailure(str(last_exc))


def _sub_concept_block(sub_concepts: list[dict]) -> str:
    return "\n".join(
        f"- {c['id']}: {c['label']} — {c['description']}" for c in sub_concepts
    )


async def extract_subconcepts(topic: str, grade_level: str) -> dict:
    """{sub_concepts: [{id, label, description}] (3-5), has_sequence: bool}"""
    user_prompt = f"Topic: {topic}\nGrade level: {grade_level}"
    return await _llm_json(EXTRACT_SUBCONCEPTS_PROMPT, user_prompt, SubConceptsResult)


async def generate_analogy(sub_concepts: list[dict], universe: str) -> dict:
    """{analogy_text: str, mapping: [{sub_concept_id, maps_to}]}"""
    user_prompt = f"Sub-concepts:\n{_sub_concept_block(sub_concepts)}\nUniverse: {universe}"
    return await _llm_json(ANALOGY_PROMPT, user_prompt, AnalogyResult)


async def generate_flashcards(topic: str, sub_concepts: list[dict]) -> dict:
    """{cards: [{question, answer, hint?}]} - exactly 3 cards."""
    user_prompt = f"Topic: {topic}\nSub-concepts:\n{_sub_concept_block(sub_concepts)}"
    return await _llm_json(FLASHCARDS_PROMPT, user_prompt, FlashcardsResult)


async def generate_mermaid(sub_concepts: list[dict]) -> dict:
    """{mermaid_source: str} - only called when has_sequence is true."""
    user_prompt = f"Sub-concepts:\n{_sub_concept_block(sub_concepts)}"
    return await _llm_json(MERMAID_PROMPT, user_prompt, MermaidResult)


async def generate_memes(topic: str, sub_concepts: list[dict]) -> dict:
    """{memes: [{caption, punchline}]} - text-only, no image generation."""
    user_prompt = f"Topic: {topic}\nSub-concepts:\n{_sub_concept_block(sub_concepts)}"
    return await _llm_json(MEMES_PROMPT, user_prompt, MemesResult)


async def evaluate_analogy(student_analogy: str, sub_concepts: list[dict]) -> dict:
    """{covered: [id], missing: [id], relationship_correct: bool, feedback}"""
    user_prompt = (
        f"Sub-concepts:\n{_sub_concept_block(sub_concepts)}\n"
        f"Student's analogy:\n{student_analogy}"
    )
    return await _llm_json(EVALUATE_PROMPT, user_prompt, EvaluateResult)


def compute_band(covered: list, missing: list, relationship_correct: bool) -> tuple[str, float]:
    """Band is computed in application code, never by the LLM."""
    total = len(covered) + len(missing)
    coverage_pct = (len(covered) / total) if total else 0.0
    if coverage_pct >= 0.80 and relationship_correct:
        band = "Strong"
    elif coverage_pct >= 0.40:
        band = "Partial"
    else:
        band = "Needs work"
    return band, round(coverage_pct * 100, 2)


_NON_ATTEMPTS = {
    "idk", "i don't know", "i dont know", "no idea", "no", "nope", "nothing",
    "dunno", "skip", "pass", "nah", "can't", "cant", "huh", "what", "?", "??",
    "i have no idea",
}


def is_real_attempt(text: str) -> bool:
    """Heuristic gate before evaluate_analogy: not empty, not purely
    non-alphabetic, not an obvious non-attempt."""
    t = (text or "").strip().lower()
    if len(t) < 15 or t in _NON_ATTEMPTS:
        return False
    if len(re.findall(r"[a-zA-Z]", t)) < 8:
        return False
    return True
