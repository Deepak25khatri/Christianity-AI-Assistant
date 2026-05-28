"""Anti-hallucination verse_validator.

Pipeline:
    1. Regex-extract every `Book Chap:Verse[-Verse]` from the draft.
    2. Look each up in the canonical Bible (bible_canonical.json).
    3. Strip nonexistent citations from the draft (and adjacent quotes if any).
    4. Fuzzy-match any quoted text adjacent to a citation against the canonical
       text. If ratio < 90 mark as partial.
    5. If anything was changed, request a single regeneration with corrective notes;
       otherwise mark `citations_verified` and proceed.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List

from rag.canonical import CitationCheck, get_canonical
from rag.state import GraphState

log = logging.getLogger(__name__)

MAX_REGEN = 1


def _audit(state: GraphState, node: str, payload: Dict, started: float) -> GraphState:
    audit = list(state.get("audit") or [])
    audit.append({"node": node, "latency_ms": int((time.time() - started) * 1000), **payload})
    state["audit"] = audit
    return state


def _strip_bad_citations(draft: str, bad: List[CitationCheck]) -> str:
    out = draft
    for c in bad:
        out = out.replace(f"({c.raw})", "[citation removed]")
        out = out.replace(c.raw, "[citation removed]")
    return out


def verse_validator(state: GraphState) -> GraphState:
    started = time.time()
    draft = state.get("draft", "")
    canonical = get_canonical()

    checks = canonical.verify_citations(draft)
    nonexistent = [c for c in checks if not c.exists]
    mismatched = [c for c in checks if c.exists and not c.text_ok]

    citations_payload: list[dict] = []
    for c in checks:
        citations_payload.append({
            "ref": c.raw,
            "book": c.book,
            "chapter": c.chapter,
            "verse_start": c.verse_start,
            "verse_end": c.verse_end,
            "exists": c.exists,
            "canonical_text": c.canonical_text,
            "quoted_text": c.quoted_text,
            "text_match_ratio": c.text_match_ratio,
            "verified": c.exists and c.text_ok,
        })

    if not checks:
        state["citations"] = []
        state["citations_verified"] = "full"  # nothing to verify -> trivially full
        state["validator_notes"] = None
        return _audit(state, "verse_validator", {"n_citations": 0, "status": "full"}, started)

    state["citations"] = citations_payload

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
        return _audit(state, "verse_validator", {"n_citations": len(checks),
                                                   "bad": len(nonexistent) + len(mismatched),
                                                   "status": "regenerate"}, started)

    # No more regenerations allowed -> strip bad citations and accept what's left.
    if nonexistent or mismatched:
        state["draft"] = _strip_bad_citations(draft, nonexistent + mismatched)
        state["citations_verified"] = "partial"
    else:
        state["citations_verified"] = "full"
    state["validator_notes"] = None
    return _audit(state, "verse_validator", {"n_citations": len(checks),
                                               "bad": len(nonexistent) + len(mismatched),
                                               "status": state["citations_verified"]}, started)
