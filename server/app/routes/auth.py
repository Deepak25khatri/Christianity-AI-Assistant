from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, hash_password, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginReq, RegisterReq, TokenResp, UpdatePrefReq

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResp)
def register(req: RegisterReq, db: Session = Depends(get_db)) -> TokenResp:
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        denomination_pref=req.denomination_pref,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResp(
        access_token=create_token(user.id),
        user_id=user.id,
        email=user.email,
        denomination_pref=user.denomination_pref,
    )


@router.post("/login", response_model=TokenResp)
def login(req: LoginReq, db: Session = Depends(get_db)) -> TokenResp:
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return TokenResp(
        access_token=create_token(user.id),
        user_id=user.id,
        email=user.email,
        denomination_pref=user.denomination_pref,
    )


@router.get("/me", response_model=TokenResp)
def me(user: User = Depends(get_current_user)) -> TokenResp:
    return TokenResp(
        access_token="",
        user_id=user.id,
        email=user.email,
        denomination_pref=user.denomination_pref,
    )


@router.patch("/me/denomination", response_model=TokenResp)
def update_denom(req: UpdatePrefReq,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> TokenResp:
    user.denomination_pref = req.denomination_pref if req.denomination_pref != "none" else None
    db.commit()
    db.refresh(user)
    return TokenResp(
        access_token="",
        user_id=user.id,
        email=user.email,
        denomination_pref=user.denomination_pref,
    )
