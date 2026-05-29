"""Standalone image-generation endpoint. Goes through the same safety subgraph."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from openai import AuthenticationError, OpenAIError

from app.auth import get_current_user
from app.models import User
from app.schemas import ImageReq, ImageResp
from rag.nodes.image import image_generate, image_policy, image_sanitize
from rag.state import GraphState

log = logging.getLogger(__name__)
router = APIRouter(prefix="/images", tags=["images"])


@router.post("", response_model=ImageResp)
async def generate_image(req: ImageReq, user: User = Depends(get_current_user)) -> ImageResp:
    state: GraphState = {
        "user_id": user.id,
        "user_message": req.prompt,
        "audit": [],
    }
    try:
        state = await image_sanitize(state)
        state = await image_policy(state)
        state = await image_generate(state)
    except AuthenticationError:
        log.exception("openai authentication failed for image request")
        return ImageResp(
            image_url=None,
            refused_reason=(
                "OpenAI API key is invalid or expired. Update OPENAI_API_KEY in your .env file "
                "and restart: docker compose up -d --build"
            ),
            sanitized_prompt=None,
        )
    except OpenAIError as exc:
        log.exception("openai error during image request")
        return ImageResp(
            image_url=None,
            refused_reason=f"Image service error: {exc}",
            sanitized_prompt=None,
        )
    except Exception as exc:
        log.exception("unexpected image request failure")
        return ImageResp(
            image_url=None,
            refused_reason=f"Unexpected error: {exc}",
            sanitized_prompt=None,
        )

    return ImageResp(
        image_url=state.get("image_url"),
        refused_reason=state.get("image_refused_reason"),
        sanitized_prompt=state.get("image_prompt_sanitized"),
    )
