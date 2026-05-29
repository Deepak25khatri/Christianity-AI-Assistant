"""Anti-hallucination verse_validator."""
from __future__ import annotations

import time

from rag.canonical import CitationCheck, get_canonical
from rag.models.citations import CitationRecord
from rag.nodes._audit import audit
from rag.state import GraphState

MAX_REGEN = 1


def _strip_bad_citations(draft: str, bad: list[CitationCheck]) -> str:
    out = draft
    for c in bad:
        out = out.replace(f"({c.raw})", "[citation removed]")
        out = out.replace(c.raw, "[citation removed]")
    return out


def _to_record(c: CitationCheck) -> CitationRecord:
    return CitationRecord(
        ref=c.raw,
        book=c.book,
        chapter=c.chapter,
        verse_start=c.verse_start,
        verse_end=c.verse_end,
        exists=c.exists,
        canonical_text=c.canonical_text,
        quoted_text=c.quoted_text,
        text_match_ratio=c.text_match_ratio,
        verified=c.exists and c.text_ok,
    )


async def verse_validator(state: GraphState) -> GraphState:
    started = time.time()
    draft = state.get("draft", "")
    canonical = get_canonical()

    checks = canonical.verify_citations(draft)
    nonexistent = [c for c in checks if not c.exists]
    mismatched = [c for c in checks if c.exists and not c.text_ok]
    records = [_to_record(c) for c in checks]

    if not checks:
        state["citations"] = []
        state["citations_verified"] = "full"
        state["validator_notes"] = None
        return audit(state, "verse_validator", {"n_citations": 0, "status": "full"}, started)

    state["citations"] = [r.model_dump() for r in records]

    attempts = int(state.get("regenerate_attempts") or 0)
    if (nonexistent or mismatched) and attempts < MAX_REGEN:
        issues = []
        for c in nonexistent:
            issues.append(f"'{c.raw}' does not exist in the canonical Bible")
        for c in mismatched:
            issues.append(
                f"'{c.raw}' quoted text does not match canonical (ratio={c.text_match_ratio:.0f}). "
                f"Canonical: \"{(c.canonical_text or '')[:160]}\""
            )
        state["validator_notes"] = "; ".join(issues)
        state["regenerate_attempts"] = attempts + 1
        state["citations_verified"] = "partial"
        return audit(
            state,
            "verse_validator",
            {"n_citations": len(checks), "bad": len(nonexistent) + len(mismatched), "status": "regenerate"},
            started,
        )

    if nonexistent or mismatched:
        state["draft"] = _strip_bad_citations(draft, nonexistent + mismatched)
        state["citations_verified"] = "partial"
    else:
        state["citations_verified"] = "full"
    state["validator_notes"] = None
    return audit(
        state,
        "verse_validator",
        {
            "n_citations": len(checks),
            "bad": len(nonexistent) + len(mismatched),
            "status": state["citations_verified"],
        },
        started,
    )
