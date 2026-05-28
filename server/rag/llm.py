"""OpenAI chat client shared by all LangGraph nodes."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

log = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_openai() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_settings().openai_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def chat_json(system: str, user: str, *, model: Optional[str] = None,
              temperature: float = 0.0) -> Dict[str, Any]:
    """Single-shot JSON-mode chat. Returns parsed dict or {}."""
    s = get_settings()
    resp = get_openai().chat.completions.create(
        model=model or s.chat_model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("non-JSON model output: %s", raw[:200])
        return {}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def chat_text(messages: List[Dict[str, str]], *, model: Optional[str] = None,
              temperature: float = 0.3) -> str:
    s = get_settings()
    resp = get_openai().chat.completions.create(
        model=model or s.chat_model,
        temperature=temperature,
        messages=messages,
    )
    return resp.choices[0].message.content or ""


def moderate(text: str) -> Dict[str, Any]:
    """Returns {flagged: bool, categories: {...}}."""
    try:
        resp = get_openai().moderations.create(model="omni-moderation-latest", input=text)
        r = resp.results[0]
        return {
            "flagged": bool(r.flagged),
            "categories": {k: bool(v) for k, v in r.categories.model_dump().items()},
        }
    except Exception as exc:
        log.warning("moderation failed (open-fail): %s", exc)
        return {"flagged": False, "categories": {}, "error": str(exc)}
