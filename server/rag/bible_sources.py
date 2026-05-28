"""Bible source loaders.

We try multiple public-domain JSON sources for resilience. All return a flat
list of verse dicts: {translation, book, chapter, verse, text}.

Primary: scrollmapper/bible_databases JSON dumps (single-file per translation).
Fallback: bibleapi/bibleapi-bibles-json (also single-file per translation).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "ChristianityAIAssistant/1.0 (+demo)"


@dataclass(frozen=True)
class BibleSource:
    translation: str
    urls: tuple[str, ...]
    parser: str


SOURCES: list[BibleSource] = [
    BibleSource(
        translation="WEB",
        urls=(
            "https://raw.githubusercontent.com/bibleapi/bibleapi-bibles-json/master/web.json",
            "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_bbe.json",
        ),
        parser="auto",
    ),
    BibleSource(
        translation="KJV",
        urls=(
            "https://raw.githubusercontent.com/bibleapi/bibleapi-bibles-json/master/kjv.json",
            "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json",
        ),
        parser="auto",
    ),
]


# Canonical book-name normalization. Maps common variants to a single form.
_BOOK_ALIASES = {
    "genesis": "Genesis", "gen": "Genesis",
    "exodus": "Exodus", "exo": "Exodus", "ex": "Exodus",
    "leviticus": "Leviticus", "lev": "Leviticus",
    "numbers": "Numbers", "num": "Numbers",
    "deuteronomy": "Deuteronomy", "deut": "Deuteronomy",
    "joshua": "Joshua", "josh": "Joshua",
    "judges": "Judges", "judg": "Judges",
    "ruth": "Ruth",
    "1 samuel": "1 Samuel", "1samuel": "1 Samuel", "i samuel": "1 Samuel", "1 sam": "1 Samuel",
    "2 samuel": "2 Samuel", "2samuel": "2 Samuel", "ii samuel": "2 Samuel", "2 sam": "2 Samuel",
    "1 kings": "1 Kings", "i kings": "1 Kings",
    "2 kings": "2 Kings", "ii kings": "2 Kings",
    "1 chronicles": "1 Chronicles", "i chronicles": "1 Chronicles",
    "2 chronicles": "2 Chronicles", "ii chronicles": "2 Chronicles",
    "ezra": "Ezra",
    "nehemiah": "Nehemiah", "neh": "Nehemiah",
    "esther": "Esther", "est": "Esther",
    "job": "Job",
    "psalms": "Psalms", "psalm": "Psalms", "ps": "Psalms",
    "proverbs": "Proverbs", "prov": "Proverbs",
    "ecclesiastes": "Ecclesiastes", "eccl": "Ecclesiastes",
    "song of solomon": "Song of Solomon", "song of songs": "Song of Solomon", "sos": "Song of Solomon",
    "isaiah": "Isaiah", "isa": "Isaiah",
    "jeremiah": "Jeremiah", "jer": "Jeremiah",
    "lamentations": "Lamentations", "lam": "Lamentations",
    "ezekiel": "Ezekiel", "ezek": "Ezekiel",
    "daniel": "Daniel", "dan": "Daniel",
    "hosea": "Hosea",
    "joel": "Joel",
    "amos": "Amos",
    "obadiah": "Obadiah", "obad": "Obadiah",
    "jonah": "Jonah",
    "micah": "Micah",
    "nahum": "Nahum",
    "habakkuk": "Habakkuk", "hab": "Habakkuk",
    "zephaniah": "Zephaniah", "zeph": "Zephaniah",
    "haggai": "Haggai", "hag": "Haggai",
    "zechariah": "Zechariah", "zech": "Zechariah",
    "malachi": "Malachi", "mal": "Malachi",
    "matthew": "Matthew", "matt": "Matthew", "mt": "Matthew",
    "mark": "Mark", "mk": "Mark",
    "luke": "Luke", "lk": "Luke",
    "john": "John", "jn": "John",
    "acts": "Acts",
    "romans": "Romans", "rom": "Romans",
    "1 corinthians": "1 Corinthians", "i corinthians": "1 Corinthians", "1 cor": "1 Corinthians",
    "2 corinthians": "2 Corinthians", "ii corinthians": "2 Corinthians", "2 cor": "2 Corinthians",
    "galatians": "Galatians", "gal": "Galatians",
    "ephesians": "Ephesians", "eph": "Ephesians",
    "philippians": "Philippians", "phil": "Philippians",
    "colossians": "Colossians", "col": "Colossians",
    "1 thessalonians": "1 Thessalonians", "i thessalonians": "1 Thessalonians", "1 thess": "1 Thessalonians",
    "2 thessalonians": "2 Thessalonians", "ii thessalonians": "2 Thessalonians", "2 thess": "2 Thessalonians",
    "1 timothy": "1 Timothy", "i timothy": "1 Timothy", "1 tim": "1 Timothy",
    "2 timothy": "2 Timothy", "ii timothy": "2 Timothy", "2 tim": "2 Timothy",
    "titus": "Titus",
    "philemon": "Philemon", "phlm": "Philemon",
    "hebrews": "Hebrews", "heb": "Hebrews",
    "james": "James", "jas": "James",
    "1 peter": "1 Peter", "i peter": "1 Peter", "1 pet": "1 Peter",
    "2 peter": "2 Peter", "ii peter": "2 Peter", "2 pet": "2 Peter",
    "1 john": "1 John", "i john": "1 John",
    "2 john": "2 John", "ii john": "2 John",
    "3 john": "3 John", "iii john": "3 John",
    "jude": "Jude",
    "revelation": "Revelation", "rev": "Revelation", "revelations": "Revelation",
}


def normalize_book(name: str) -> str:
    key = name.strip().lower()
    key = re.sub(r"\s+", " ", key)
    return _BOOK_ALIASES.get(key, name.strip())


def _coerce_verse_payload(raw: dict) -> Optional[dict]:
    """Try to extract {book, chapter, verse, text} from various JSON shapes."""
    book = raw.get("book_name") or raw.get("book") or raw.get("b")
    chapter = raw.get("chapter") or raw.get("c")
    verse = raw.get("verse") or raw.get("v")
    text = raw.get("text") or raw.get("t")
    if not (book and chapter and verse and text):
        return None
    try:
        return {
            "book": normalize_book(str(book)),
            "chapter": int(chapter),
            "verse": int(verse),
            "text": str(text).strip(),
        }
    except (ValueError, TypeError):
        return None


def _flatten(data) -> Iterable[dict]:
    """Yield verse rows from any of the common JSON shapes."""
    if isinstance(data, dict):
        if "verses" in data and isinstance(data["verses"], list):
            yield from (v for v in data["verses"])
            return
        if "resultset" in data and isinstance(data["resultset"], dict):
            rows = data["resultset"].get("row") or []
            for row in rows:
                fields = row.get("field") if isinstance(row, dict) else None
                if fields and len(fields) >= 5:
                    yield {"book": fields[1], "chapter": fields[2], "verse": fields[3], "text": fields[4]}
            return
        for v in data.values():
            yield from _flatten(v)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and ("text" in item or "t" in item):
                yield item
            else:
                yield from _flatten(item)


def fetch_translation(source: BibleSource, client: httpx.Client) -> List[dict]:
    last_err: Optional[Exception] = None
    for url in source.urls:
        try:
            log.info("fetching %s from %s", source.translation, url)
            resp = client.get(url, timeout=60.0, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            verses: list[dict] = []
            for raw in _flatten(data):
                row = _coerce_verse_payload(raw)
                if row:
                    row["translation"] = source.translation
                    verses.append(row)
            if len(verses) > 1000:
                log.info("parsed %d verses for %s", len(verses), source.translation)
                return verses
            log.warning("source %s only yielded %d verses, trying next", url, len(verses))
        except Exception as exc:
            log.warning("source %s failed: %s", url, exc)
            last_err = exc
    raise RuntimeError(f"all sources failed for {source.translation}: {last_err}")


def load_all_translations() -> List[dict]:
    out: list[dict] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for src in SOURCES:
            try:
                out.extend(fetch_translation(src, client))
            except Exception as exc:
                log.error("skipping %s: %s", src.translation, exc)
    return out
