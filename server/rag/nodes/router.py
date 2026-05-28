"""Intent router + denomination resolver."""
from __future__ import annotations

import time
from typing import Dict

from rag.llm import chat_json
from rag.prompts import DENOM_INFER_SYSTEM, ROUTER_SYSTEM
from rag.state import GraphState


def _audit(state: GraphState, node: str, payload: Dict, started: float) -> GraphState:
    audit = list(state.get("audit") or [])
    audit.append({
        "node": node,
        "latency_ms": int((time.time() - started) * 1000),
        **payload,
    })
    state["audit"] = audit
    return state


def router(state: GraphState) -> GraphState:
    started = time.time()
    msg = state.get("user_message", "")
    out = chat_json(ROUTER_SYSTEM, msg)
    intent = out.get("intent", "theological_q")
    if intent not in ("scripture_lookup", "theological_q", "content_generation",
                      "image_request", "smalltalk"):
        intent = "theological_q"
    state["intent"] = intent
    return _audit(state, "router", {"intent": intent}, started)


def denom_resolver(state: GraphState) -> GraphState:
    started = time.time()
    pref = state.get("denomination_pref")
    if pref and pref != "none":
        state["denomination"] = pref
        return _audit(state, "denom_resolver", {"source": "user_pref", "denomination": pref}, started)

    history = state.get("messages") or []
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
    transcript += f"\nuser: {state.get('user_message','')}"
    out = chat_json(DENOM_INFER_SYSTEM, transcript)
    denom = out.get("denomination", "none")
    conf = float(out.get("confidence", 0.0) or 0.0)
    if denom not in ("catholic", "protestant", "orthodox", "none"):
        denom = "none"
    if conf < 0.6:
        denom = "none"
    state["denomination"] = denom
    return _audit(state, "denom_resolver", {"source": "inferred", "denomination": denom, "confidence": conf}, started)
