"""Finalize node: assemble the response object handed back to the API."""
from __future__ import annotations

import time
from typing import Dict

from rag.state import GraphState


def _audit(state: GraphState, node: str, payload: Dict, started: float) -> GraphState:
    audit = list(state.get("audit") or [])
    audit.append({"node": node, "latency_ms": int((time.time() - started) * 1000), **payload})
    state["audit"] = audit
    return state


def finalize(state: GraphState) -> GraphState:
    started = time.time()
    if not state.get("final_content"):
        state["final_content"] = state.get("draft", "")

    safety_flags = dict(state.get("safety_flags") or {})
    safety_flags.setdefault("input_label", state.get("safety_label", "safe"))
    safety_flags.setdefault("output_blocked", bool(state.get("output_blocked")))
    safety_flags.setdefault("citations_verified", state.get("citations_verified", "none"))
    state["safety_flags"] = safety_flags

    return _audit(state, "finalize", {"len": len(state["final_content"])}, started)
