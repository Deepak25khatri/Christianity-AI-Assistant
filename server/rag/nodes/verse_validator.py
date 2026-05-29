"""Anti-hallucination verse_validator."""
from __future__ import annotations

import re
import time

from rag.canonical import CitationCheck, citation_overlaps_retrieved, get_canonical
from rag.models.citations import CitationRecord
from rag.nodes._audit import audit
from rag.state import GraphState

MAX_REGEN = 1


def _strip_bad_citations(draft: str, bad: list[CitationCheck]) -> str:
    """Remove failed citations from user-visible text (no placeholder markers)."""
    out = draft
    for c in bad:
        for token in (f"({c.raw})", f'"{c.raw}"', c.raw):
            out = out.replace(token, "")
    out = re.sub(r"\[citation removed\]", "", out, flags=re.IGNORECASE)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r'"\s*"', "", out)
    out = re.sub(r"  +", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _to_record(c: CitationCheck) -> CitationRecord:
    verified = c.exists and c.text_ok and c.grounded_in_retrieval
    return CitationRecord(
        ref=c.raw,
        book=c.book,
        chapter=c.chapter,
        verse_start=c.verse_start,
        verse_end=c.verse_end,
        exists=c.exists,
        canonical_text=c.canonical_text,
        quoted_text=c.quoted_text,
        text_match_ratio=c.text_match_ratio or 0.0,
        grounded_in_retrieval=c.grounded_in_retrieval,
        verified=verified,
    )


def _annotate_grounding(checks: list[CitationCheck], retrieved: list) -> None:
    for c in checks:
        if c.exists:
            c.grounded_in_retrieval = citation_overlaps_retrieved(
                c.book, c.chapter, c.verse_start, c.verse_end, retrieved
            )
        else:
            c.grounded_in_retrieval = False


def _bad_checks(checks: list[CitationCheck]) -> list[CitationCheck]:
    return [
        c for c in checks
        if not c.exists or (c.exists and not c.text_ok) or (c.exists and not c.grounded_in_retrieval)
    ]


async def verse_validator(state: GraphState) -> GraphState:
    started = time.time()
    draft = state.get("draft", "")
    canonical = get_canonical()
    retrieved = state.get("retrieved") or []

    checks = canonical.verify_citations(draft)
    _annotate_grounding(checks, retrieved)
    bad = _bad_checks(checks)
    nonexistent = [c for c in checks if not c.exists]
    mismatched = [c for c in checks if c.exists and not c.text_ok]
    ungrounded = [c for c in checks if c.exists and c.text_ok and not c.grounded_in_retrieval]
    records = [_to_record(c) for c in checks]

    if not checks:
        state["citations"] = []
        state["citations_verified"] = "full"
        state["validator_notes"] = None
        return audit(state, "verse_validator", {"n_citations": 0, "status": "full"}, started)

    state["citations"] = [r.model_dump() for r in records]

    attempts = int(state.get("regenerate_attempts") or 0)
    if bad and attempts < MAX_REGEN:
        issues = []
        for c in nonexistent:
            issues.append(f"'{c.raw}' does not exist in the canonical Bible")
        for c in mismatched:
            issues.append(
                f"'{c.raw}' quoted text does not match canonical (ratio={c.text_match_ratio:.0f}). "
                f"Canonical: \"{(c.canonical_text or '')[:160]}\""
            )
        for c in ungrounded:
            issues.append(f"'{c.raw}' exists but was not in retrieved context")
        state["validator_notes"] = "; ".join(issues)
        state["regenerate_attempts"] = attempts + 1
        state["citations_verified"] = "partial"
        return audit(
            state,
            "verse_validator",
            {
                "n_citations": len(checks),
                "bad": len(bad),
                "ungrounded": len(ungrounded),
                "status": "regenerate",
            },
            started,
        )

    if bad:
        state["draft"] = _strip_bad_citations(draft, bad)
        checks = canonical.verify_citations(state["draft"])
        _annotate_grounding(checks, retrieved)
        records = [_to_record(c) for c in checks]
        state["citations"] = [r.model_dump() for r in records]
        if records and all(r.verified for r in records):
            state["citations_verified"] = "full"
        elif any(r.verified for r in records):
            state["citations_verified"] = "partial"
        else:
            state["citations_verified"] = "none"
    else:
        state["citations_verified"] = "full"
    state["validator_notes"] = None
    return audit(
        state,
        "verse_validator",
        {
            "n_citations": len(checks),
            "bad": len(bad),
            "ungrounded": len(ungrounded),
            "status": state["citations_verified"],
        },
        started,
    )
