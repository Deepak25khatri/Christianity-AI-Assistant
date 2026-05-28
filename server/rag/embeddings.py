"""Embedding helper. Batched, with retry."""
from __future__ import annotations

import logging
from typing import List

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

log = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_settings().openai_api_key)
    return _client


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=10))
def _embed_batch(texts: List[str], model: str) -> List[List[float]]:
    resp = _get_client().embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def embed_texts(texts: List[str], batch_size: int = 96) -> List[List[float]]:
    if not texts:
        return []
    model = get_settings().embed_model
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        log.info("embedding batch %d-%d / %d", i, i + len(batch), len(texts))
        out.extend(_embed_batch(batch, model))
    return out


def embed_one(text: str) -> List[float]:
    return embed_texts([text])[0]
