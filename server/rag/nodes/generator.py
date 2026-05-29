"""Generator node + corrective regeneration."""
from __future__ import annotations

import time

from rag.llm import achat_text
from rag.nodes._audit import audit
from rag.prompt_loader import format_prompt, get_prompt
from rag.state import GraphState, Message


def _format_context(state: GraphState) -> str:
    retrieved = state.get("retrieved") or []
    if not retrieved:
        return "(no relevant passages retrieved)"
    lines: list[str] = []
    for i, doc in enumerate(retrieved, 1):
        if doc.get("source_type") == "scripture":
            head = (
                f"[{i}] Scripture: {doc.get('book')} {doc.get('chapter')}:"
                f"{doc.get('verse_start')}-{doc.get('verse_end')} ({doc.get('translation')})"
            )
        else:
            head = f"[{i}] Commentary ({doc.get('denomination', 'shared')}): {doc.get('title', '')}"
        lines.append(f"{head}\n{doc.get('text', '').strip()}\n")
    return "\n".join(lines)


def _build_messages(state: GraphState, regen_issues: str | None) -> list[Message]:
    compare = bool(state.get("compare_traditions"))
    comparison_instructions = (
        format_prompt(
            "generator",
            "comparison_instructions",
            denomination=state.get("denomination") or "none",
        )
        if compare
        else get_prompt("generator", "standard_instructions")
    )
    system = format_prompt(
        "generator",
        "system",
        denomination=state.get("denomination") or "unknown",
        comparison_instructions=comparison_instructions,
        context=_format_context(state),
    )
    messages: list[Message] = [{"role": "system", "content": system}]
    for m in (state.get("messages") or [])[-10:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": state.get("user_message", "")})
    if regen_issues:
        messages.append({
            "role": "system",
            "content": format_prompt("generator", "regeneration_note", issues=regen_issues),
        })
    return messages


async def generator(state: GraphState) -> GraphState:
    started = time.time()
    attempts = int(state.get("regenerate_attempts") or 0)
    issues = state.get("validator_notes") if attempts > 0 else None
    messages = _build_messages(state, issues)
    draft = await achat_text(messages, temperature=0.4)
    state["draft"] = draft
    return audit(state, "generator", {"attempts": attempts, "draft_len": len(draft)}, started)
