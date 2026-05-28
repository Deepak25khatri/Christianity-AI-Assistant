"""Standalone image-generation endpoint. Goes through the same safety subgraph."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import User
from app.schemas import ImageReq, ImageResp
from rag.nodes.image import image_generate, image_policy, image_sanitize
from rag.state import GraphState

router = APIRouter(prefix="/images", tags=["images"])


@router.post("", response_model=ImageResp)
def generate_image(req: ImageReq, user: User = Depends(get_current_user)) -> ImageResp:
    state: GraphState = {
        "user_id": user.id,
        "user_message": req.prompt,
        "audit": [],
    }
    state = image_sanitize(state)
    state = image_policy(state)
    state = image_generate(state)
    return ImageResp(
        image_url=state.get("image_url"),
        refused_reason=state.get("image_refused_reason"),
        sanitized_prompt=state.get("image_prompt_sanitized"),
    )
