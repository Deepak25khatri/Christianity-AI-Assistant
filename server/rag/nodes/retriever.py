"""Hybrid retriever: Qdrant dense + BM25 + Reciprocal Rank Fusion."""
from __future__ import annotations

import logging
import os
import pickle
import time
from functools import lru_cache
from typing import Dict, List, Tuple

from app.config import get_settings
from rag.embeddings import embed_one
from rag.qdrant_store import get_client, search
from rag.state import GraphState, RetrievedDoc

log = logging.getLogger(__name__)

TOP_DENSE = 20
TOP_BM25 = 20
RRF_K = 60
FINAL_K = 6
FINAL_K_COMPARE = 8

_COMPARE_HINTS = (
    "difference", "differences", "compare", "comparison", "versus", " vs ",
    "catholic", "protestant", "orthodox", "traditions", "denominations",
)


def _is_tradition_comparison(query: str) -> bool:
    q = query.lower()
    trad_hits = sum(1 for t in ("catholic", "protestant", "orthodox", "orthodoxy") if t in q)
    if trad_hits >= 2:
        return True
    return any(h in q for h in _COMPARE_HINTS) and trad_hits >= 1


def _ensure_tradition_diversity(candidates: list[RetrievedDoc], limit: int) -> list[RetrievedDoc]:
    """For comparison answers, prefer a mix of commentary traditions + scripture."""
    scripture = [d for d in candidates if d.get("source_type") == "scripture"]
    commentary = [d for d in candidates if d.get("source_type") == "commentary"]
    picked: list[RetrievedDoc] = []
    seen: set[str] = set()

    def add(doc: RetrievedDoc) -> None:
        key = (doc.get("text") or "")[:120]
        if key and key not in seen:
            seen.add(key)
            picked.append(doc)

    for doc in scripture[:3]:
        add(doc)

    for trad in ("shared", "catholic", "orthodox", "protestant"):
        for doc in commentary:
            if (doc.get("denomination") or "shared") == trad:
                add(doc)
                break

    for doc in candidates:
        if len(picked) >= limit:
            break
        add(doc)

    return picked[:limit]


@lru_cache(maxsize=1)
def _load_bm25():
    path = get_settings().bm25_index_path
    if not os.path.exists(path):
        log.warning("bm25 index not found at %s; BM25 retrieval will be no-op", path)
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def _tokenize(text: str) -> List[str]:
    return [t for t in text.lower().split() if t.strip()]


def _audit(state: GraphState, node: str, payload: Dict, started: float) -> GraphState:
    audit = list(state.get("audit") or [])
    audit.append({"node": node, "latency_ms": int((time.time() - started) * 1000), **payload})
    state["audit"] = audit
    return state


def _rrf(rankings: List[List[str]], k: int = RRF_K) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _denomination_filter(state: GraphState) -> List[str]:
    pref = state.get("denomination") or "none"
    if pref == "none":
        return []  # no filter -> all denominations allowed
    return [pref, "shared"]


def retriever(state: GraphState) -> GraphState:
    started = time.time()
    query = state.get("user_message", "")
    if not query.strip():
        state["retrieved"] = []
        return _audit(state, "retriever", {"n": 0}, started)

    denom_filter = _denomination_filter(state)
    compare_mode = _is_tradition_comparison(query)
    if compare_mode:
        denom_filter = []  # pull commentary from all traditions
        state["compare_traditions"] = True
    else:
        state["compare_traditions"] = False

    # 1) Dense search via Qdrant
    final_k = FINAL_K_COMPARE if compare_mode else FINAL_K
    qvec = embed_one(query)
    qclient = get_client()
    dense_hits = search(
        qclient,
        vector=qvec,
        limit=TOP_DENSE,
        denomination_filter=denom_filter or None,
    )
    dense_lookup: Dict[str, dict] = {}
    dense_order: list[str] = []
    for hit in dense_hits:
        key = str(hit.id)
        dense_lookup[key] = {"payload": hit.payload, "score": float(hit.score)}
        dense_order.append(key)

    # 2) BM25 over the in-memory pickle
    bm25_order: list[str] = []
    bm25_lookup: Dict[str, dict] = {}
    bm25_blob = _load_bm25()
    if bm25_blob is not None:
        bm25 = bm25_blob["bm25"]
        payloads = bm25_blob["payloads"]
        scores = bm25.get_scores(_tokenize(query))
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:TOP_BM25]
        for i in top_idx:
            pl = payloads[i]
            if denom_filter and pl.get("denomination") not in denom_filter:
                continue
            key = f"bm25:{i}"
            bm25_lookup[key] = {"payload": pl, "score": float(scores[i])}
            bm25_order.append(key)

    # 3) RRF fusion. We treat dense ids and bm25 ids as distinct namespaces, then
    # dedupe in the post-step by payload text to avoid double-listing the same chunk.
    fused = _rrf([dense_order, bm25_order])
    seen_texts: set[str] = set()
    candidates: list[RetrievedDoc] = []
    for doc_id, fscore in fused:
        entry = dense_lookup.get(doc_id) or bm25_lookup.get(doc_id)
        if not entry:
            continue
        pl = entry["payload"]
        txt = (pl.get("text") or "").strip()
        if not txt or txt in seen_texts:
            continue
        seen_texts.add(txt)
        candidates.append({
            "text": txt,
            "score": float(fscore),
            "source_type": pl.get("source_type", "unknown"),
            "book": pl.get("book"),
            "chapter": pl.get("chapter"),
            "verse_start": pl.get("verse_start"),
            "verse_end": pl.get("verse_end"),
            "translation": pl.get("translation"),
            "denomination": pl.get("denomination"),
            "title": pl.get("title"),
        })

    final = _ensure_tradition_diversity(candidates, final_k) if compare_mode else candidates[:final_k]

    state["retrieved"] = final
    return _audit(state, "retriever", {
        "dense": len(dense_order), "bm25": len(bm25_order), "final": len(final),
        "compare_mode": compare_mode,
    }, started)
