"""Conversation message endpoints, including the SSE streaming endpoint."""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth import get_current_user
from app.db import SessionLocal, get_db
from app.graph_runner import load_history, persist_turn, run_graph
from app.models import Conversation, Message, User
from app.schemas import MessageOut, SendMessageReq
from rag.graph import build_graph

log = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["messages"])

CHUNK_CHARS = 28


def _ensure_owner(db: Session, conversation_id: str, user_id: int) -> Conversation:
    convo = db.get(Conversation, conversation_id)
    if not convo or convo.user_id != user_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    return convo


@router.post("/{conversation_id}/messages", response_model=MessageOut)
async def send_message_sync(
    conversation_id: str,
    req: SendMessageReq,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageOut:
    _ensure_owner(db, conversation_id, user.id)
    final_state = await run_graph(db, req.content, conversation_id, user.denomination_pref, user.id)
    msg = persist_turn(db, conversation_id, req.content, final_state)
    return MessageOut.model_validate(msg)


@router.get("/{conversation_id}/stream")
async def stream_message(
    conversation_id: str,
    content: str,
    token: str,
    request: Request,
) -> EventSourceResponse:
    from app.auth import decode_token

    user_id = decode_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid token")

    db = SessionLocal()
    try:
        convo = db.get(Conversation, conversation_id)
        if not convo or convo.user_id != user_id:
            raise HTTPException(status_code=404, detail="conversation not found")
        user = db.get(User, user_id)
        denomination_pref = user.denomination_pref if user else None
        history = load_history(db, conversation_id)
    finally:
        db.close()

    async def event_gen():
        seen_audit = 0
        final_state: dict[str, Any] = {}
        local_db = SessionLocal()
        try:
            state_in: dict[str, Any] = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "user_message": content,
                "messages": history,
                "denomination_pref": denomination_pref,
                "audit": [],
            }
            graph_app = build_graph()
            async for ev in graph_app.astream(state_in, {"recursion_limit": 25}):
                if await request.is_disconnected():
                    break
                for _node, partial in ev.items():
                    if isinstance(partial, dict):
                        final_state.update(partial)
                        audit = final_state.get("audit") or []
                        for entry in audit[seen_audit:]:
                            yield {"event": "node", "data": json.dumps(entry, default=str)}
                        seen_audit = len(audit)

            for c in final_state.get("citations") or []:
                yield {"event": "citation", "data": json.dumps(c, default=str)}

            safety = final_state.get("safety_flags") or {}
            yield {"event": "safety", "data": json.dumps(safety, default=str)}

            if final_state.get("image_url"):
                yield {
                    "event": "image",
                    "data": json.dumps({"url": final_state["image_url"]}, default=str),
                }

            text = final_state.get("final_content", "")
            for i in range(0, len(text), CHUNK_CHARS):
                chunk = text[i:i + CHUNK_CHARS]
                yield {"event": "token", "data": json.dumps({"text": chunk}, default=str)}

            persisted = persist_turn(local_db, conversation_id, content, final_state)
            yield {"event": "done", "data": json.dumps({"message_id": persisted.id}, default=str)}
        except Exception as exc:
            log.exception("graph stream failed")
            yield {"event": "stream_error", "data": json.dumps({"error": str(exc)}, default=str)}
        finally:
            local_db.close()

    return EventSourceResponse(event_gen())
