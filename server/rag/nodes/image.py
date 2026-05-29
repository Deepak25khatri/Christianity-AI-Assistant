"""Image-generation sub-graph nodes."""
from __future__ import annotations

import logging
import time

from rag.llm import achat_json_model, get_async_openai
from rag.models.image import ImagePolicyResult, ImageSanitizeResult
from rag.nodes._audit import audit
from rag.prompt_loader import get_prompt, get_refusal
from rag.state import GraphState
from app.config import get_settings

log = logging.getLogger(__name__)


async def image_sanitize(state: GraphState) -> GraphState:
    started = time.time()
    out = await achat_json_model(
        get_prompt("image_sanitize", "system"),
        state.get("user_message", ""),
        ImageSanitizeResult,
    )
    if out.blocked:
        state["image_refused_reason"] = out.reason or "Request violates Christian image policy."
        state["image_prompt_sanitized"] = None
        return audit(state, "image_sanitize", {"blocked": True, "reason": out.reason}, started)
    state["image_prompt_sanitized"] = out.prompt
    return audit(state, "image_sanitize", {"blocked": False}, started)


async def image_policy(state: GraphState) -> GraphState:
    started = time.time()
    if state.get("image_refused_reason"):
        return audit(state, "image_policy", {"skipped": True}, started)
    prompt = state.get("image_prompt_sanitized") or ""
    out = await achat_json_model(get_prompt("image_policy", "system"), prompt, ImagePolicyResult)
    if not out.allow:
        state["image_refused_reason"] = out.reason or "Blocked by image policy."
    return audit(state, "image_policy", out.model_dump(), started)


async def image_generate(state: GraphState) -> GraphState:
    started = time.time()
    if state.get("image_refused_reason"):
        state["final_content"] = (
            get_refusal("image_blocked") + f"\n\n_Reason: {state['image_refused_reason']}_"
        )
        state["safety_flags"] = {
            "refused": True,
            "label": "image_blocked",
            "reason": state["image_refused_reason"],
        }
        return audit(state, "image_generate", {"refused": True}, started)

    s = get_settings()
    prompt = state.get("image_prompt_sanitized") or state.get("user_message", "")
    try:
        client = get_async_openai()
        resp = await client.images.generate(
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
        state["final_content"] = get_refusal("image_blocked")
        state["safety_flags"] = {"refused": True, "label": "image_error", "reason": str(exc)}
    return audit(state, "image_generate", {"ok": "image_url" in state}, started)
