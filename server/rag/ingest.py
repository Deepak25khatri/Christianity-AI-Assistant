"""End-to-end ingestion: Bible JSON + commentary -> canonical store + Qdrant.

Run inside the docker `ingest` profile or locally:
    python -m rag.ingest
    python -m rag.ingest --force  # rebuild even if collection exists

Chunking strategy:
    - Verses are atomic, kept 1:1 in bible_canonical.json.
    - Retrieval chunks are sliding 5-verse passage windows (stride 3), so
      cross-verse semantics survive without losing precise verse anchors.
    - Commentary uses LangChain RecursiveCharacterTextSplitter (900 / 150).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import sys
import uuid
from collections import defaultdict
from typing import Dict, List, Tuple

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.http import models as qm
from rank_bm25 import BM25Okapi

from app.config import get_settings
from rag.bible_sources import load_all_translations
from rag.embeddings import embed_texts
from rag.qdrant_store import (
    collection_count,
    ensure_collection,
    get_client,
    upsert_points,
)
from rag.seed_commentary import SEED as COMMENTARY_SEED

log = logging.getLogger("rag.ingest")

WINDOW = 5
STRIDE = 3


def _tokenize(text: str) -> List[str]:
    return [t for t in text.lower().split() if t.strip()]


def _write_canonical(verses: List[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    log.info("writing canonical bible (%d verses) to %s", len(verses), path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False)


def _build_passage_windows(verses: List[dict]) -> List[Tuple[str, dict]]:
    """Return list of (text, payload) tuples for retrieval."""
    by_loc: Dict[Tuple[str, str, int], List[dict]] = defaultdict(list)
    for v in verses:
        by_loc[(v["translation"], v["book"], int(v["chapter"]))].append(v)

    chunks: list[tuple[str, dict]] = []
    for (translation, book, chapter), rows in by_loc.items():
        rows.sort(key=lambda r: int(r["verse"]))
        if not rows:
            continue
        n = len(rows)
        i = 0
        while i < n:
            window = rows[i:i + WINDOW]
            if not window:
                break
            v_start = int(window[0]["verse"])
            v_end = int(window[-1]["verse"])
            text = " ".join(f'{w["text"].strip()}' for w in window)
            text = f"[{book} {chapter}:{v_start}-{v_end} {translation}] {text}"
            payload = {
                "source_type": "scripture",
                "translation": translation,
                "book": book,
                "chapter": chapter,
                "verse_start": v_start,
                "verse_end": v_end,
                "denomination": "shared",  # canonical scripture is denomination-shared
                "text": text,
            }
            chunks.append((text, payload))
            if i + WINDOW >= n:
                break
            i += STRIDE
    return chunks


def _build_commentary_chunks() -> List[Tuple[str, dict]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    out: list[tuple[str, dict]] = []
    for doc in COMMENTARY_SEED:
        for piece in splitter.split_text(doc["text"]):
            payload = {
                "source_type": "commentary",
                "translation": None,
                "book": None,
                "chapter": None,
                "verse_start": None,
                "verse_end": None,
                "denomination": doc["denomination"],
                "title": doc["title"],
                "source": doc["source"],
                "text": piece,
            }
            out.append((piece, payload))
    return out


def _save_bm25_index(chunks: List[Tuple[str, dict]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    corpus_tokens = [_tokenize(text) for text, _ in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    with open(path, "wb") as f:
        pickle.dump({"bm25": bm25, "payloads": [p for _, p in chunks], "texts": [t for t, _ in chunks]}, f)
    log.info("saved BM25 index (%d docs) to %s", len(chunks), path)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Rebuild even if Qdrant collection is populated")
    args = parser.parse_args()

    settings = get_settings()
    client = get_client()
    ensure_collection(client)

    if not args.force and collection_count(client) > 0:
        log.info("collection already has %d points; skipping (use --force to rebuild)",
                 collection_count(client))
        return 0

    log.info("loading Bible translations from public sources...")
    verses = load_all_translations()
    if not verses:
        log.error("no Bible verses loaded - aborting")
        return 1
    log.info("loaded %d verses across %d translations",
             len(verses), len({v["translation"] for v in verses}))

    _write_canonical(verses, settings.canonical_bible_path)

    log.info("building passage windows...")
    scripture_chunks = _build_passage_windows(verses)
    log.info("built %d scripture passage windows", len(scripture_chunks))

    log.info("building commentary chunks...")
    commentary_chunks = _build_commentary_chunks()
    log.info("built %d commentary chunks", len(commentary_chunks))

    all_chunks = scripture_chunks + commentary_chunks
    log.info("total chunks: %d", len(all_chunks))

    _save_bm25_index(all_chunks, settings.bm25_index_path)

    log.info("embedding chunks...")
    texts = [c[0] for c in all_chunks]
    vectors = embed_texts(texts)

    log.info("upserting to Qdrant in batches...")
    BATCH = 256
    for i in range(0, len(all_chunks), BATCH):
        batch = all_chunks[i:i + BATCH]
        batch_vecs = vectors[i:i + BATCH]
        points = [
            qm.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload=payload,
            )
            for (_text, payload), vec in zip(batch, batch_vecs)
        ]
        upsert_points(client, points)
        log.info("upserted %d / %d", min(i + BATCH, len(all_chunks)), len(all_chunks))

    log.info("ingest complete. final collection count: %d", collection_count(client))
    return 0


if __name__ == "__main__":
    sys.exit(main())
