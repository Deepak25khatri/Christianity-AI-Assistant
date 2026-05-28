"""Thin Qdrant wrapper used by the ingest pipeline and the hybrid retriever."""
from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import get_settings

log = logging.getLogger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-3-small


def get_client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url, timeout=60.0)


def ensure_collection(client: QdrantClient, name: Optional[str] = None) -> None:
    s = get_settings()
    coll = name or s.qdrant_collection
    existing = {c.name for c in client.get_collections().collections}
    if coll in existing:
        log.info("qdrant collection %s already exists", coll)
        return
    log.info("creating qdrant collection %s", coll)
    client.create_collection(
        collection_name=coll,
        vectors_config=qm.VectorParams(size=EMBEDDING_DIM, distance=qm.Distance.COSINE),
    )
    for field in ("denomination", "source_type", "translation", "book"):
        client.create_payload_index(
            collection_name=coll,
            field_name=field,
            field_schema=qm.PayloadSchemaType.KEYWORD,
        )


def collection_count(client: QdrantClient, name: Optional[str] = None) -> int:
    s = get_settings()
    coll = name or s.qdrant_collection
    try:
        return client.count(collection_name=coll, exact=True).count
    except Exception:
        return 0


def upsert_points(client: QdrantClient, points: List[qm.PointStruct], name: Optional[str] = None) -> None:
    s = get_settings()
    coll = name or s.qdrant_collection
    client.upsert(collection_name=coll, points=points, wait=True)


def search(
    client: QdrantClient,
    vector: List[float],
    *,
    limit: int = 20,
    denomination_filter: Optional[List[str]] = None,
    source_type_filter: Optional[List[str]] = None,
    name: Optional[str] = None,
):
    s = get_settings()
    coll = name or s.qdrant_collection
    must: list[qm.FieldCondition] = []
    if denomination_filter:
        must.append(qm.FieldCondition(
            key="denomination",
            match=qm.MatchAny(any=denomination_filter),
        ))
    if source_type_filter:
        must.append(qm.FieldCondition(
            key="source_type",
            match=qm.MatchAny(any=source_type_filter),
        ))
def search(
    client: QdrantClient,
    vector: List[float],
    *,
    limit: int = 20,
    denomination_filter: Optional[List[str]] = None,
    source_type_filter: Optional[List[str]] = None,
    name: Optional[str] = None,
):
    s = get_settings()
    coll = name or s.qdrant_collection
    must: list[qm.FieldCondition] = []
    if denomination_filter:
        must.append(qm.FieldCondition(
            key="denomination",
            match=qm.MatchAny(any=denomination_filter),
        ))
    if source_type_filter:
        must.append(qm.FieldCondition(
            key="source_type",
            match=qm.MatchAny(any=source_type_filter),
        ))
    flt = qm.Filter(must=must) if must else None
    try:
        return client.search(
            collection_name=coll,
            query_vector=vector,
            limit=limit,
            query_filter=flt,
            with_payload=True,
        )
    except Exception as exc:
        log.warning("qdrant search failed (collection may be empty): %s", exc)
        return []
