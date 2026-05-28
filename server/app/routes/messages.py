"""Conversation message endpoints, including the SSE streaming endpoint.

Design note: we stream high-signal events (node start/finish, citation,
safety, image, done) plus the assistant content split into ~30-char chunks so
the UI has a "typing" feel. The graph itself runs in a worker thread; events
are pushed onto an asyncio.Queue that the SSE generator drains.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

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
def send_message_sync(conversation_id: str, req: SendMessageReq,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> MessageOut:
    _ensure_owner(db, conversation_id, user.id)
    final_state = run_graph(db, req.content, conversation_id, user.denomination_pref, user.id)
    msg = persist_turn(db, conversation_id, req.content, final_state)
    return MessageOut.model_validate(msg)


@router.get("/{conversation_id}/stream")
async def stream_message(conversation_id: str, content: str, token: str,
                            request: Request) -> EventSourceResponse:
    """SSE endpoint. Auth via `token` query param (EventSource cannot set headers).

    Emits events:
        node     : {node, latency_ms, ...payload}
        token    : {text}
        citation : {ref, verified, canonical_text}
        safety   : {citations_verified, refused, label}
        image    : {url}
        done     : {message_id}
        error    : {error}
    """
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

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def graph_worker():
        seen_audit = 0

        def progress_state(state):
            nonlocal seen_audit
            audit = state.get("audit") or []
            for entry in audit[seen_audit:]:
                loop.call_soon_threadsafe(queue.put_nowait,
                                          {"event": "node", "data": entry})
            seen_audit = len(audit)

        local_db = SessionLocal()
        try:
            state_in: Dict[str, Any] = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "user_message": content,
                "messages": history,
                "denomination_pref": denomination_pref,
                "audit": [],
            }
            graph_app = build_graph()
            final_state: Dict[str, Any] = {}
            for ev in graph_app.stream(state_in, {"recursion_limit": 25}):
                for _node, partial in ev.items():
                    if isinstance(partial, dict):
                        final_state.update(partial)
                        progress_state(final_state)

            for c in final_state.get("citations") or []:
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "citation", "data": c})

            safety = final_state.get("safety_flags") or {}
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "safety", "data": safety})

            if final_state.get("image_url"):
                loop.call_soon_threadsafe(queue.put_nowait,
                                          {"event": "image", "data": {"url": final_state["image_url"]}})

            text = final_state.get("final_content", "")
            for i in range(0, len(text), CHUNK_CHARS):
                chunk = text[i:i + CHUNK_CHARS]
                loop.call_soon_threadsafe(queue.put_nowait,
                                          {"event": "token", "data": {"text": chunk}})

            persisted = persist_turn(local_db, conversation_id, content, final_state)
            loop.call_soon_threadsafe(queue.put_nowait,
                                      {"event": "done", "data": {"message_id": persisted.id}})
        except Exception as exc:
            log.exception("graph worker failed")
            loop.call_soon_threadsafe(queue.put_nowait,
                                      {"event": "stream_error", "data": {"error": str(exc)}})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "_end", "data": None})
            local_db.close()

    loop.run_in_executor(None, graph_worker)

    async def event_gen():
        while True:
            if await request.is_disconnected():
                break
            msg = await queue.get()
            if msg["event"] == "_end":
                break
            yield {"event": msg["event"], "data": json.dumps(msg["data"], default=str)}

    return EventSourceResponse(event_gen())
