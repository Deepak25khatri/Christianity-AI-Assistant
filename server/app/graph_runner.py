"""Adapter between the FastAPI route layer and the LangGraph app.

Responsibilities:
    - hydrate state from SQLite (last N user/assistant messages)
    - run the graph (sync; LangGraph is invoked in a thread for SSE streaming)
    - persist the assistant message + audit log
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, Conversation, Message
from rag.graph import build_graph

log = logging.getLogger(__name__)

HISTORY_TURNS = 12

_graph = None


def get_graph_app():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def load_history(db: Session, conversation_id: str, n: int = HISTORY_TURNS) -> List[Dict[str, str]]:
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(n)
        .all()
    )
    rows = list(reversed(rows))
    return [{"role": r.role, "content": r.content} for r in rows]


def persist_turn(
    db: Session,
    conversation_id: str,
    user_text: str,
    final_state: Dict[str, Any],
) -> Message:
    user_msg = Message(conversation_id=conversation_id, role="user", content=user_text)
    db.add(user_msg)
    db.flush()

    citations = final_state.get("citations") or []
    safety = final_state.get("safety_flags") or {}
    retrieved = final_state.get("retrieved") or []
    verified = (safety.get("citations_verified") or final_state.get("citations_verified")
                or "none")
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=final_state.get("final_content", ""),
        citations_json=citations,
        safety_flags_json=safety,
        retrieved_json=retrieved,
        citations_verified=verified,
        image_url=final_state.get("image_url"),
    )
    db.add(assistant_msg)
    db.flush()

    for entry in final_state.get("audit") or []:
        db.add(AuditLog(
            message_id=assistant_msg.id,
            node_name=entry.get("node", "unknown"),
            payload_json={k: v for k, v in entry.items() if k not in ("node", "latency_ms")},
            latency_ms=entry.get("latency_ms"),
        ))

    convo = db.get(Conversation, conversation_id)
    if convo and (not convo.title or convo.title == "New conversation"):
        convo.title = (user_text[:60] + ("..." if len(user_text) > 60 else ""))

    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg


def run_graph(
    db: Session,
    user_text: str,
    conversation_id: str,
    denomination_pref: Optional[str],
    user_id: int,
) -> Dict[str, Any]:
    history = load_history(db, conversation_id)
    state: Dict[str, Any] = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "user_message": user_text,
        "messages": history,
        "denomination_pref": denomination_pref,
        "audit": [],
    }
    app = get_graph_app()
    final_state = app.invoke(state, {"recursion_limit": 25})
    return final_state
