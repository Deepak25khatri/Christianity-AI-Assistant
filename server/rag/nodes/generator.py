"""Generator node + corrective regeneration."""
from __future__ import annotations

import time
from typing import Dict, List

from rag.llm import chat_text
from rag.prompts import (
    GENERATOR_COMPARISON_INSTRUCTIONS,
    GENERATOR_REGENERATION_NOTE,
    GENERATOR_STANDARD_INSTRUCTIONS,
    GENERATOR_SYSTEM,
)
from rag.state import GraphState, Message


def _audit(state: GraphState, node: str, payload: Dict, started: float) -> GraphState:
    audit = list(state.get("audit") or [])
    audit.append({"node": node, "latency_ms": int((time.time() - started) * 1000), **payload})
    state["audit"] = audit
    return state


def _format_context(state: GraphState) -> str:
    retrieved = state.get("retrieved") or []
    if not retrieved:
        return "(no relevant passages retrieved)"
    lines: list[str] = []
    for i, doc in enumerate(retrieved, 1):
        if doc.get("source_type") == "scripture":
            head = f"[{i}] Scripture: {doc.get('book')} {doc.get('chapter')}:" \
                   f"{doc.get('verse_start')}-{doc.get('verse_end')} ({doc.get('translation')})"
        else:
            head = f"[{i}] Commentary ({doc.get('denomination','shared')}): {doc.get('title','')}"
        lines.append(f"{head}\n{doc.get('text','').strip()}\n")
    return "\n".join(lines)


def _build_messages(state: GraphState, regen_issues: str | None) -> List[Message]:
    compare = bool(state.get("compare_traditions"))
    comparison_instructions = (
        GENERATOR_COMPARISON_INSTRUCTIONS.format(
            denomination=state.get("denomination") or "none",
        )
        if compare
        else GENERATOR_STANDARD_INSTRUCTIONS
    )
    system = GENERATOR_SYSTEM.format(
        denomination=state.get("denomination") or "unknown",
        comparison_instructions=comparison_instructions,
        context=_format_context(state),
    )
    messages: List[Message] = [{"role": "system", "content": system}]
    for m in (state.get("messages") or [])[-10:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": state.get("user_message", "")})
    if regen_issues:
        messages.append({
            "role": "system",
            "content": GENERATOR_REGENERATION_NOTE.format(issues=regen_issues),
        })
    return messages


def generator(state: GraphState) -> GraphState:
    started = time.time()
    attempts = int(state.get("regenerate_attempts") or 0)
    issues = state.get("validator_notes") if attempts > 0 else None
    messages = _build_messages(state, issues)
    draft = chat_text(messages, temperature=0.4)
    state["draft"] = draft
    return _audit(state, "generator", {"attempts": attempts, "draft_len": len(draft)}, started)
