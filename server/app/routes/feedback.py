from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import Conversation, Feedback, Message, User
from app.schemas import FeedbackReq

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
def submit_feedback(req: FeedbackReq,
                     user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)) -> dict:
    msg = db.get(Message, req.message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="message not found")
    convo = db.get(Conversation, msg.conversation_id)
    if not convo or convo.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your message")
    fb = Feedback(message_id=msg.id, user_id=user.id, rating=req.rating, note=req.note)
    db.add(fb)
    db.commit()
    return {"ok": True, "id": fb.id}
