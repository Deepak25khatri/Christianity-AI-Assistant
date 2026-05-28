from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Conversation, Message, User
from app.schemas import ConversationCreate, ConversationOut, MessageOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> list[ConversationOut]:
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return [ConversationOut.model_validate(c) for c in rows]


@router.post("", response_model=ConversationOut)
def create_conversation(req: ConversationCreate,
                          user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)) -> ConversationOut:
    convo = Conversation(user_id=user.id, title=req.title or "New conversation")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return ConversationOut.model_validate(convo)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: str,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> list[MessageOut]:
    convo = db.get(Conversation, conversation_id)
    if not convo or convo.user_id != user.id:
        raise HTTPException(status_code=404, detail="conversation not found")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [MessageOut.model_validate(m) for m in msgs]


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str,
                          user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)) -> dict:
    convo = db.get(Conversation, conversation_id)
    if not convo or convo.user_id != user.id:
        raise HTTPException(status_code=404, detail="conversation not found")
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(convo)
    db.commit()
    return {"deleted": conversation_id}
