"""Agentic orchestrator.

Drives the Gemini model through the tutoring sequence using NATIVE structured
tool calls (OpenAI-compatible `tools` / `tool_choice` params) - no prompt-based
JSON parsing for tool dispatch. Inner tool functions make their own llm_client
calls with dedicated prompts (each with its own single retry).
"""
import json

from .llm_client import LLMError, complete_with_retry
from .prompts import SYSTEM_PROMPT_TEMPLATE
from .tools import (
    ToolFailure,
    compute_band,
    evaluate_analogy,
    extract_subconcepts,
    generate_analogy,
    generate_flashcards,
    generate_memes,
    generate_mermaid,
    is_real_attempt,
)

MAX_TOOL_ROUNDS = 10

NON_ATTEMPT_NOTE = (
    "non_attempt: the student's input was empty, gibberish, or not a real "
    "attempt. Do NOT evaluate. Respond with a warm, specific, encouraging "
    "nudge inviting a real attempt, even a rough one, and wait for their "
    "next message."
)

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "extract_subconcepts",
            "description": (
                "Break a topic into 3-5 sub-concepts calibrated to the "
                "student's grade level, and report whether they form a "
                "sequence. Call this first for every new topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_analogy",
            "description": (
                "Generate an analogy that maps each sub-concept onto the "
                "student's preferred universe."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "universe": {
                        "type": "string",
                        "description": "Optional override of the student's preferred universe.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_flashcards",
            "description": "Generate exactly 3 question/answer flashcards for the current topic.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_mermaid",
            "description": (
                "Generate a Mermaid flowchart of the sub-concepts' sequence. "
                "Only call when has_sequence is true."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_memes",
            "description": (
                "Generate 2-3 short text-only meme-style jokes about the "
                "topic as memory hooks."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_analogy",
            "description": (
                "Evaluate the student's teach-back attempt against the "
                "sub-concepts. Only call when the student made a real attempt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "student_analogy": {
                        "type": "string",
                        "description": "The student's own analogy, quoted or paraphrased in full.",
                    }
                },
                "required": ["student_analogy"],
            },
        },
    },
]


def build_system_prompt(profile: dict) -> str:
    grade = profile.get("grade_level") or "middle school"
    universe = profile.get("preferred_universe") or "everyday life"
    return SYSTEM_PROMPT_TEMPLATE.replace("{{grade_level}}", grade).replace(
        "{{preferred_universe}}", universe
    )


def _result(state: dict) -> dict:
    return {
        "assets": state["assets"],
        "session_update": state["session_update"],
        "evaluation": state["evaluation"],
    }


async def run_turn(profile: dict, session: dict, history: list[dict], user_message: str) -> dict:
    """Run one orchestrator turn.

    Returns {reply, error, assets, session_update, evaluation}. On any tool
    or LLM failure (after the single retry), returns error=True so the API
    layer persists NOTHING partial and answers with the plain message.
    """
    state = {
        "assets": [],
        "session_update": None,
        "evaluation": None,
        "sub_concepts": session.get("sub_concepts") or [],
    }
    messages: list[dict] = [dict(m) for m in history]
    messages.append({"role": "user", "content": user_message})

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            resp = await complete_with_retry(
                build_system_prompt(profile), messages, tools=TOOL_SPECS
            )
            msg = resp["choices"][0]["message"]
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return {"reply": msg.get("content") or "", "error": False, **_result(state)}
            messages.append(
                {"role": "assistant", "content": msg.get("content"), "tool_calls": tool_calls}
            )
            for tc in tool_calls:
                content = await _execute_tool(tc, profile, session, state)
                messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": content}
                )
        # The model never produced a final answer.
        return {"reply": "", "error": True, **_result(state)}
    except (ToolFailure, LLMError, KeyError, ValueError):
        return {"reply": "", "error": True, **_result(state)}


async def _execute_tool(tc: dict, profile: dict, session: dict, state: dict) -> str:
    """Execute one model-requested tool call and return the JSON content for
    the tool-role message. ToolFailure propagates and aborts the whole turn."""
    try:
        fn = tc["function"]
        name = fn["name"]
        args = json.loads(fn.get("arguments") or "{}")
    except (KeyError, json.JSONDecodeError):
        return json.dumps({"error": "malformed tool call"})

    try:
        if name == "extract_subconcepts":
            topic = args.get("topic") or session.get("topic") or ""
            data = await extract_subconcepts(
                topic, profile.get("grade_level") or "middle school"
            )
            state["sub_concepts"] = data["sub_concepts"]
            state["session_update"] = {
                "sub_concepts": data["sub_concepts"],
                "has_sequence": data["has_sequence"],
            }
            return json.dumps(data)

        if name == "generate_analogy":
            universe = (
                args.get("universe")
                or profile.get("preferred_universe")
                or "everyday life"
            )
            data = await generate_analogy(state["sub_concepts"], universe)
            state["assets"].append({"asset_type": "analogy", "content": data})
            return json.dumps(data)

        if name == "generate_flashcards":
            data = await generate_flashcards(
                session.get("topic") or args.get("topic") or "", state["sub_concepts"]
            )
            state["assets"].append({"asset_type": "flashcards", "content": data})
            return json.dumps(data)

        if name == "generate_mermaid":
            seq = (state.get("session_update") or {}).get("has_sequence")
            if not (seq or session.get("has_sequence")):
                return json.dumps({"note": "has_sequence is false; skip the flowchart."})
            data = await generate_mermaid(state["sub_concepts"])
            state["assets"].append({"asset_type": "mermaid", "content": data})
            return json.dumps(data)

        if name == "generate_memes":
            data = await generate_memes(
                session.get("topic") or "", state["sub_concepts"]
            )
            state["assets"].append({"asset_type": "memes", "content": data})
            return json.dumps(data)

        if name == "evaluate_analogy":
            student_analogy = (args.get("student_analogy") or "").strip()
            # Orchestrator-side heuristic gate - never evaluate a non-attempt.
            if not is_real_attempt(student_analogy):
                return json.dumps({"note": NON_ATTEMPT_NOTE})
            result = await evaluate_analogy(student_analogy, state["sub_concepts"])
            # Band is computed in application code, never by the LLM.
            band, coverage_pct = compute_band(
                result["covered"], result["missing"], result["relationship_correct"]
            )
            labels = {c["id"]: c["label"] for c in state["sub_concepts"]}
            state["evaluation"] = {
                "student_analogy": student_analogy,
                **result,
                "band": band,
                "coverage_pct": coverage_pct,
                "covered_labels": [labels.get(i, i) for i in result["covered"]],
                "missing_labels": [labels.get(i, i) for i in result["missing"]],
            }
            state["assets"].append(
                {"asset_type": "evaluation", "content": state["evaluation"]}
            )
            return json.dumps({**result, "band": band, "coverage_pct": coverage_pct})

        return json.dumps({"error": f"unknown tool: {name}"})
    except ToolFailure:
        raise
