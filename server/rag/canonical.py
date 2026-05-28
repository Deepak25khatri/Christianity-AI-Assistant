"""Canonical verse store used by the anti-hallucination verse_validator.

This is a one-shot in-memory dict keyed by `(translation, book, chapter, verse)`
plus a default-translation lookup. Loaded from the JSON the ingest step writes
to `data/bible_canonical.json`.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple

from rapidfuzz import fuzz

from .bible_sources import normalize_book

log = logging.getLogger(__name__)

DEFAULT_TRANSLATION = "WEB"

# Citation parser: matches "John 3:16", "1 Cor 13:4-7", "Romans 8:28", etc.
CITATION_RE = re.compile(
    r"\b(?:(?P<num>[1-3])\s+)?(?P<book>(?:[A-Z][a-z]+)(?:\s+of\s+[A-Z][a-z]+)?)"
    r"\s+(?P<chap>\d{1,3}):(?P<v1>\d{1,3})(?:[-\u2013](?P<v2>\d{1,3}))?",
    re.UNICODE,
)


@dataclass(frozen=True)
class Verse:
    translation: str
    book: str
    chapter: int
    verse: int
    text: str


@dataclass
class CitationCheck:
    raw: str
    book: str
    chapter: int
    verse_start: int
    verse_end: int
    exists: bool
    quoted_text: Optional[str] = None
    canonical_text: Optional[str] = None
    text_match_ratio: Optional[float] = None

    @property
    def text_ok(self) -> bool:
        if self.quoted_text is None:
            return True  # citation without inline quote -> only existence matters
        return (self.text_match_ratio or 0) >= 90.0


class CanonicalBible:
    def __init__(self, verses: Iterable[Verse]):
        self._by_key: Dict[Tuple[str, str, int, int], Verse] = {}
        for v in verses:
            self._by_key[(v.translation, v.book, v.chapter, v.verse)] = v

    @classmethod
    def from_json(cls, path: str) -> "CanonicalBible":
        if not os.path.exists(path):
            log.warning("canonical bible not found at %s; verse_validator will be permissive", path)
            return cls([])
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            Verse(
                translation=row["translation"],
                book=row["book"],
                chapter=int(row["chapter"]),
                verse=int(row["verse"]),
                text=row["text"],
            )
            for row in data
        )

    def __len__(self) -> int:
        return len(self._by_key)

    def lookup(self, book: str, chapter: int, verse: int, translation: str = DEFAULT_TRANSLATION) -> Optional[Verse]:
        book = normalize_book(book)
        v = self._by_key.get((translation, book, chapter, verse))
        if v is not None:
            return v
        # fallback to any translation if requested one is missing
        for t in ("WEB", "KJV"):
            v = self._by_key.get((t, book, chapter, verse))
            if v is not None:
                return v
        return None

    def get_range(self, book: str, chapter: int, v_start: int, v_end: int,
                  translation: str = DEFAULT_TRANSLATION) -> List[Verse]:
        out = []
        for v in range(v_start, v_end + 1):
            row = self.lookup(book, chapter, v, translation)
            if row:
                out.append(row)
        return out

    def extract_citations(self, text: str) -> List[Tuple[str, dict]]:
        out: list[tuple[str, dict]] = []
        for m in CITATION_RE.finditer(text):
            book_part = m.group("book").strip()
            num = m.group("num")
            book_full = f"{num} {book_part}" if num else book_part
            book_norm = normalize_book(book_full)
            out.append((
                m.group(0),
                {
                    "book": book_norm,
                    "chapter": int(m.group("chap")),
                    "verse_start": int(m.group("v1")),
                    "verse_end": int(m.group("v2") or m.group("v1")),
                },
            ))
        return out

    def verify_citations(self, draft: str, translation: str = DEFAULT_TRANSLATION) -> List[CitationCheck]:
        checks: list[CitationCheck] = []
        for raw, parsed in self.extract_citations(draft):
            verses = self.get_range(parsed["book"], parsed["chapter"],
                                    parsed["verse_start"], parsed["verse_end"], translation)
            exists = len(verses) > 0
            quoted = self._adjacent_quote(draft, raw)
            canonical_text = " ".join(v.text for v in verses) if verses else None
            ratio = None
            if quoted and canonical_text:
                ratio = float(fuzz.partial_ratio(quoted, canonical_text))
            checks.append(CitationCheck(
                raw=raw,
                book=parsed["book"],
                chapter=parsed["chapter"],
                verse_start=parsed["verse_start"],
                verse_end=parsed["verse_end"],
                exists=exists,
                quoted_text=quoted,
                canonical_text=canonical_text,
                text_match_ratio=ratio,
            ))
        return checks

    @staticmethod
    def _adjacent_quote(text: str, ref: str) -> Optional[str]:
        """If the citation appears next to a quoted string, return that quoted text."""
        idx = text.find(ref)
        if idx == -1:
            return None
        window_start = max(0, idx - 400)
        window_end = min(len(text), idx + len(ref) + 400)
        window = text[window_start:window_end]
        quote_match = re.search(r'"([^"]{8,})"', window) or re.search(r"\u201C([^\u201D]{8,})\u201D", window)
        return quote_match.group(1).strip() if quote_match else None


@lru_cache(maxsize=1)
def get_canonical(path: Optional[str] = None) -> CanonicalBible:
    from app.config import get_settings
    actual = path or get_settings().canonical_bible_path
    return CanonicalBible.from_json(actual)
