"""Async OpenAI chat client shared by all LangGraph nodes."""
from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from openai import AsyncOpenAI, AuthenticationError
from pydantic import BaseModel
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from rag.models.guards import ModerationResult

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None


def get_async_openai() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    return _client


@retry(
    retry=retry_if_not_exception_type(AuthenticationError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
)
async def achat_json_raw(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> dict[str, Any]:
    s = get_settings()
    resp = await get_async_openai().chat.completions.create(
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


async def achat_json_model(
    system: str,
    user: str,
    model_cls: type[T],
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> T:
    data = await achat_json_raw(system, user, model=model, temperature=temperature)
    return model_cls.model_validate(data)


@retry(
    retry=retry_if_not_exception_type(AuthenticationError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
)
async def achat_text(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.3,
) -> str:
    s = get_settings()
    resp = await get_async_openai().chat.completions.create(
        model=model or s.chat_model,
        temperature=temperature,
        messages=messages,
    )
    return resp.choices[0].message.content or ""


async def amoderate(text: str) -> ModerationResult:
    try:
        resp = await get_async_openai().moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        r = resp.results[0]
        return ModerationResult(
            flagged=bool(r.flagged),
            categories={k: bool(v) for k, v in r.categories.model_dump().items()},
        )
    except Exception as exc:
        log.warning("moderation failed (open-fail): %s", exc)
        return ModerationResult(flagged=False, categories={}, error=str(exc))
