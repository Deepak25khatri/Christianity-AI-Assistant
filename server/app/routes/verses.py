"""Verse lookup endpoint used by the frontend's citation drawer to display the
canonical text behind a citation chip - this is what proves a citation is real."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import VerseLookupResp
from rag.canonical import get_canonical

router = APIRouter(prefix="/verses", tags=["verses"])


@router.get("", response_model=VerseLookupResp)
def lookup(
    book: str = Query(...),
    chapter: int = Query(...),
    verse_start: int = Query(...),
    verse_end: int = Query(None),
    translation: str = Query("WEB"),
) -> VerseLookupResp:
    canonical = get_canonical()
    v_end = verse_end or verse_start
    verses = canonical.get_range(book, chapter, verse_start, v_end, translation)
    if not verses:
        raise HTTPException(status_code=404, detail="verse not found in canonical store")
    return VerseLookupResp(
        book=verses[0].book,
        chapter=verses[0].chapter,
        verse_start=verses[0].verse,
        verse_end=verses[-1].verse,
        translation=verses[0].translation,
        text=" ".join(v.text for v in verses),
        exists=True,
    )
