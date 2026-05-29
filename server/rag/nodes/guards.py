"""Input + output safety guards via NeMo Guardrails."""
from __future__ import annotations

import time

from rag.guardrails_service import check_input, check_output
from rag.models.enums import SafetyLabel
from rag.nodes._audit import audit
from rag.prompt_loader import get_refusal, refusal_templates
from rag.state import GraphState


async def input_guard(state: GraphState) -> GraphState:
    started = time.time()
    msg = state.get("user_message", "")

    result = await check_input(msg)
    state["safety_label"] = result.label.value
    state["safety_reason"] = result.reason
    state["blocked_input"] = result.blocked
    return audit(state, "input_guard", result.model_dump(mode="json", exclude={"blocked"}), started)


async def output_guard(state: GraphState) -> GraphState:
    started = time.time()
    draft = state.get("draft", "")

    result = await check_output(draft)
    state["output_blocked"] = result.block
    state["output_block_reason"] = result.reason if result.block else None
    return audit(state, "output_guard", result.model_dump(mode="json"), started)


async def refusal_node(state: GraphState) -> GraphState:
    label = state.get("safety_label", SafetyLabel.POLICY_VIOLATION.value)
    if state.get("output_blocked"):
        label = "output_blocked"
    if state.get("image_refused_reason"):
        label = "image_blocked"

    templates = refusal_templates()
    state["final_content"] = get_refusal(label) or templates.get("policy_violation", "")
    state["safety_flags"] = {
        "refused": True,
        "label": label,
        "reason": (
            state.get("safety_reason")
            or state.get("output_block_reason")
            or state.get("image_refused_reason")
        ),
    }
    return state
