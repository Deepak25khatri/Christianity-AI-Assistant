"""Finalize node: assemble the response object handed back to the API."""
from __future__ import annotations

import re
import time

from rag.nodes._audit import audit
from rag.state import GraphState


def _polish_user_text(text: str) -> str:
    """Remove internal validator artifacts before the user sees the reply."""
    out = re.sub(r"\[citation removed\]", "", text, flags=re.IGNORECASE)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"  +", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


async def finalize(state: GraphState) -> GraphState:
    started = time.time()
    if not state.get("final_content"):
        state["final_content"] = _polish_user_text(state.get("draft", ""))
    else:
        state["final_content"] = _polish_user_text(state["final_content"])

    safety_flags = dict(state.get("safety_flags") or {})
    safety_flags.setdefault("input_label", state.get("safety_label", "safe"))
    safety_flags.setdefault("output_blocked", bool(state.get("output_blocked")))
    safety_flags.setdefault("citations_verified", state.get("citations_verified", "none"))
    retrieved = state.get("retrieved") or []
    traditions = sorted({
        (d.get("denomination") or "shared")
        for d in retrieved
        if d.get("source_type") == "commentary"
    })
    if state.get("compare_traditions") and traditions:
        safety_flags["traditions_compared"] = traditions
    state["safety_flags"] = safety_flags

    return audit(state, "finalize", {"len": len(state["final_content"])}, started)
