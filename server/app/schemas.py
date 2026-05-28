"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


Denomination = Literal["catholic", "protestant", "orthodox", "none"]


class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    denomination_pref: Optional[Denomination] = None


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    denomination_pref: Optional[Denomination] = None


class UpdatePrefReq(BaseModel):
    denomination_pref: Denomination


class ConversationCreate(BaseModel):
    title: Optional[str] = "New conversation"


class ConversationOut(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations_json: Optional[Any] = None
    safety_flags_json: Optional[Any] = None
    retrieved_json: Optional[Any] = None
    citations_verified: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageReq(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ImageReq(BaseModel):
    prompt: str = Field(min_length=1, max_length=600)


class ImageResp(BaseModel):
    image_url: Optional[str] = None
    refused_reason: Optional[str] = None
    sanitized_prompt: Optional[str] = None


class FeedbackReq(BaseModel):
    message_id: int
    rating: Literal[-1, 1]
    note: Optional[str] = None


class VerseLookupResp(BaseModel):
    book: str
    chapter: int
    verse_start: int
    verse_end: int
    translation: str
    text: str
    exists: bool
