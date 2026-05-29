"""Shared LangGraph state schema."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict


Role = Literal["user", "assistant", "system"]
Denomination = Literal["catholic", "protestant", "orthodox", "none", "shared"]
Intent = Literal["scripture_lookup", "theological_q", "content_generation",
                 "image_request", "smalltalk", "unsafe"]
SafetyLabel = Literal["safe", "adversarial", "heretical_rewrite", "policy_violation"]
Verified = Literal["full", "partial", "none"]


class Message(TypedDict):
    role: Role
    content: str


class RetrievedDoc(TypedDict, total=False):
    text: str
    score: float
    source_type: str
    book: Optional[str]
    chapter: Optional[int]
    verse_start: Optional[int]
    verse_end: Optional[int]
    translation: Optional[str]
    denomination: Optional[str]
    title: Optional[str]


class GraphState(TypedDict, total=False):
    # input
    user_id: Optional[int]
    conversation_id: Optional[str]
    messages: List[Message]
    user_message: str
    denomination_pref: Optional[Denomination]

    # input_guard outputs
    safety_label: SafetyLabel
    safety_reason: Optional[str]
    blocked_input: bool

    # router
    intent: Intent

    # denom_resolver
    denomination: Denomination

    # retriever
    retrieved: List[RetrievedDoc]

    # generator
    draft: str
    regenerate_attempts: int

    # verse_validator
    citations: List[Dict[str, Any]]
    citations_verified: Verified
    validator_notes: Optional[str]

    # output_guard
    output_blocked: bool
    output_block_reason: Optional[str]

    # image flow
    image_prompt_sanitized: Optional[str]
    image_url: Optional[str]
    image_refused_reason: Optional[str]

    # retriever flags
    compare_traditions: bool

    # final
    final_content: str
    safety_flags: Dict[str, Any]
    audit: List[Dict[str, Any]]
