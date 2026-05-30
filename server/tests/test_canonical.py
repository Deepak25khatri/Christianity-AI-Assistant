"""Tests for citation parsing and retrieval overlap (no API calls)."""
from __future__ import annotations

from rag.canonical import CanonicalBible, CitationCheck, citation_overlaps_retrieved


def test_extract_citation_john_3_16():
    bible = CanonicalBible([])
    found = bible.extract_citations("See (John 3:16) for the gospel.")
    assert len(found) == 1
    raw, parsed = found[0]
    assert "John" in raw
    assert parsed["book"] == "John"
    assert parsed["chapter"] == 3
    assert parsed["verse_start"] == 16


def test_extract_citation_range():
    bible = CanonicalBible([])
    found = bible.extract_citations("Read 1 Corinthians 13:4-7.")
    assert len(found) >= 1
    _, parsed = found[0]
    assert parsed["book"] == "1 Corinthians"
    assert parsed["verse_start"] == 4
    assert parsed["verse_end"] == 7


def test_fake_book_not_exists():
    bible = CanonicalBible([])
    checks = bible.verify_citations("Explain 2 Hesitations 4:12.")
    assert len(checks) == 1
    assert checks[0].exists is False


def test_citation_overlaps_retrieved():
    retrieved = [
        {
            "source_type": "scripture",
            "book": "John",
            "chapter": 3,
            "verse_start": 14,
            "verse_end": 18,
            "text": "[John 3:14-18 WEB] ...",
        },
        {
            "source_type": "commentary",
            "book": None,
            "chapter": None,
            "verse_start": None,
            "verse_end": None,
            "text": "commentary",
        },
    ]
    assert citation_overlaps_retrieved("John", 3, 16, 16, retrieved)
    assert not citation_overlaps_retrieved("John", 3, 1, 1, retrieved)
    assert not citation_overlaps_retrieved("Romans", 8, 28, 28, retrieved)


def test_citation_check_grounded_flag():
    c = CitationCheck(
        raw="John 3:16",
        book="John",
        chapter=3,
        verse_start=16,
        verse_end=16,
        exists=True,
        grounded_in_retrieval=True,
    )
    assert c.text_ok
    c.grounded_in_retrieval = False
    from rag.models.citations import CitationRecord

    rec = CitationRecord(
        ref=c.raw,
        book=c.book,
        chapter=c.chapter,
        verse_start=c.verse_start,
        verse_end=c.verse_end,
        exists=c.exists,
        grounded_in_retrieval=c.grounded_in_retrieval,
        verified=c.exists and c.text_ok and c.grounded_in_retrieval,
    )
    assert rec.verified is False
