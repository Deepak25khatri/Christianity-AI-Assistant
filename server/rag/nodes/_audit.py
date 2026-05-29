from __future__ import annotations

import time
from typing import Any

from rag.state import GraphState


def audit(state: GraphState, node: str, payload: dict[str, Any], started: float) -> GraphState:
    audit_log = list(state.get("audit") or [])
    audit_log.append({
        "node": node,
        "latency_ms": int((time.time() - started) * 1000),
        **payload,
    })
    state["audit"] = audit_log
    return state
