from __future__ import annotations

from pydantic import BaseModel, Field


class CitationRecord(BaseModel):
    ref: str
    book: str | None = None
    chapter: int | None = None
    verse_start: int | None = None
    verse_end: int | None = None
    exists: bool = False
    canonical_text: str | None = None
    quoted_text: str | None = None
    text_match_ratio: float = 0.0
    grounded_in_retrieval: bool = False
    verified: bool = False


class ValidatorResult(BaseModel):
    citations: list[CitationRecord] = Field(default_factory=list)
    citations_verified: str = "none"
    validator_notes: str | None = None
    regenerate: bool = False
    draft: str | None = None
