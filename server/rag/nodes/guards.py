"""Input + output safety guards."""
from __future__ import annotations

import logging
import re
import time
from typing import Dict

from rag.llm import chat_json, moderate
from rag.prompts import INPUT_GUARD_SYSTEM, OUTPUT_GUARD_SYSTEM, REFUSAL_TEMPLATES
from rag.state import GraphState

log = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"ignore (all )?previous (instructions|prompts|rules)",
    r"disregard (the )?(system|above)",
    r"you are now (a|an)",
    r"pretend you are",
    r"act as (?:if you are )?(god|jesus|the holy spirit|the bible)",
    r"reveal (your )?(system|hidden) prompt",
    r"\bDAN\b",
    r"role[- ]?play as",
]
_INJ_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def _audit(state: GraphState, node: str, payload: Dict, started: float) -> GraphState:
    audit = list(state.get("audit") or [])
    audit.append({
        "node": node,
        "latency_ms": int((time.time() - started) * 1000),
        **payload,
    })
    state["audit"] = audit
    return state


def input_guard(state: GraphState) -> GraphState:
    started = time.time()
    msg = state.get("user_message", "")

    mod = moderate(msg)
    if mod.get("flagged"):
        state["safety_label"] = "policy_violation"
        state["safety_reason"] = f"moderation: {[k for k,v in mod.get('categories',{}).items() if v]}"
        state["blocked_input"] = True
        return _audit(state, "input_guard", {"flagged": True, "via": "moderation"}, started)

    if _INJ_RE.search(msg):
        state["safety_label"] = "adversarial"
        state["safety_reason"] = "prompt-injection pattern matched"
        state["blocked_input"] = True
        return _audit(state, "input_guard", {"flagged": True, "via": "regex"}, started)

    cls = chat_json(INPUT_GUARD_SYSTEM, msg)
    label = cls.get("label", "safe")
    if label not in ("safe", "adversarial", "heretical_rewrite", "policy_violation"):
        label = "safe"
    state["safety_label"] = label
    state["safety_reason"] = cls.get("reason")
    state["blocked_input"] = label != "safe"
    return _audit(state, "input_guard", {"label": label, "reason": cls.get("reason")}, started)


def output_guard(state: GraphState) -> GraphState:
    started = time.time()
    draft = state.get("draft", "")

    mod = moderate(draft)
    if mod.get("flagged"):
        state["output_blocked"] = True
        state["output_block_reason"] = "post-output moderation flagged"
        return _audit(state, "output_guard", {"flagged": True, "via": "moderation"}, started)

    cls = chat_json(OUTPUT_GUARD_SYSTEM, draft)
    blocked = bool(cls.get("block", False))
    state["output_blocked"] = blocked
    state["output_block_reason"] = cls.get("reason") if blocked else None
    return _audit(state, "output_guard", {"block": blocked, "reason": cls.get("reason")}, started)


def refusal_node(state: GraphState) -> GraphState:
    label = state.get("safety_label", "policy_violation")
    if state.get("output_blocked"):
        label = "output_blocked"
    if state.get("image_refused_reason"):
        label = "image_blocked"
    state["final_content"] = REFUSAL_TEMPLATES.get(label, REFUSAL_TEMPLATES["policy_violation"])
    state["safety_flags"] = {
        "refused": True,
        "label": label,
        "reason": state.get("safety_reason") or state.get("output_block_reason") or state.get("image_refused_reason"),
    }
    return state
