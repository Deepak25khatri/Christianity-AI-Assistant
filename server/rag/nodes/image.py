"""Image-generation sub-graph nodes.

These run only after input_guard has marked the message as safe and the router
classified it as an image_request. Even then, the sanitizer + policy classifier
can still refuse.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Dict

from openai import OpenAI

from app.config import get_settings
from rag.llm import chat_json, get_openai
from rag.prompts import (
    IMAGE_POLICY_SYSTEM,
    IMAGE_PROMPT_SANITIZER_SYSTEM,
    REFUSAL_TEMPLATES,
)
from rag.state import GraphState

log = logging.getLogger(__name__)


def _audit(state: GraphState, node: str, payload: Dict, started: float) -> GraphState:
    audit = list(state.get("audit") or [])
    audit.append({"node": node, "latency_ms": int((time.time() - started) * 1000), **payload})
    state["audit"] = audit
    return state


def image_sanitize(state: GraphState) -> GraphState:
    started = time.time()
    out = chat_json(IMAGE_PROMPT_SANITIZER_SYSTEM, state.get("user_message", ""))
    prompt = (out.get("prompt") or "").strip()
    reason = out.get("reason") or ""
    if not prompt or prompt.upper().startswith("BLOCK"):
        state["image_refused_reason"] = reason or "Request violates Christian image policy."
        state["image_prompt_sanitized"] = None
        return _audit(state, "image_sanitize", {"blocked": True, "reason": reason}, started)
    state["image_prompt_sanitized"] = prompt
    return _audit(state, "image_sanitize", {"blocked": False}, started)


def image_policy(state: GraphState) -> GraphState:
    started = time.time()
    if state.get("image_refused_reason"):
        return _audit(state, "image_policy", {"skipped": True}, started)
    prompt = state.get("image_prompt_sanitized") or ""
    out = chat_json(IMAGE_POLICY_SYSTEM, prompt)
    allow = bool(out.get("allow", False))
    if not allow:
        state["image_refused_reason"] = out.get("reason") or "Blocked by image policy."
    return _audit(state, "image_policy", {"allow": allow, "reason": out.get("reason")}, started)


def image_generate(state: GraphState) -> GraphState:
    started = time.time()
    if state.get("image_refused_reason"):
        state["final_content"] = REFUSAL_TEMPLATES["image_blocked"] + f"\n\n_Reason: {state['image_refused_reason']}_"
        state["safety_flags"] = {"refused": True, "label": "image_blocked",
                                  "reason": state["image_refused_reason"]}
        return _audit(state, "image_generate", {"refused": True}, started)

    s = get_settings()
    prompt = state.get("image_prompt_sanitized") or state.get("user_message", "")
    try:
        client: OpenAI = get_openai()
        resp = client.images.generate(
            model=s.image_model,
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        item = resp.data[0]
        url = getattr(item, "url", None)
        b64 = getattr(item, "b64_json", None)
        if url:
            image_ref = url
        elif b64:
            image_ref = f"data:image/png;base64,{b64}"
        else:
            raise RuntimeError("image API returned no url or b64")
        state["image_url"] = image_ref
        state["final_content"] = (
            f"Here is an image generated from a reverent rewrite of your request:\n\n"
            f"_Prompt used:_ {prompt}"
        )
        state["safety_flags"] = {"refused": False, "label": "image_ok"}
    except Exception as exc:
        log.exception("image generation failed")
        state["image_refused_reason"] = f"image generation failed: {exc}"
        state["final_content"] = REFUSAL_TEMPLATES["image_blocked"]
        state["safety_flags"] = {"refused": True, "label": "image_error", "reason": str(exc)}
    return _audit(state, "image_generate", {"ok": "image_url" in state}, started)
