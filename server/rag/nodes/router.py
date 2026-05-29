"""Intent router + denomination resolver."""
from __future__ import annotations

import time

from rag.llm import achat_json_model
from rag.models.enums import Denomination
from rag.models.router import DenomInferResult, RouterResult
from rag.nodes._audit import audit
from rag.prompt_loader import get_prompt
from rag.state import GraphState


async def router(state: GraphState) -> GraphState:
    started = time.time()
    msg = state.get("user_message", "")
    out = await achat_json_model(get_prompt("router", "system"), msg, RouterResult)
    state["intent"] = out.intent.value
    return audit(state, "router", {"intent": out.intent.value}, started)


async def denom_resolver(state: GraphState) -> GraphState:
    started = time.time()
    pref = state.get("denomination_pref")
    if pref and pref != Denomination.NONE.value:
        state["denomination"] = pref
        return audit(state, "denom_resolver", {"source": "user_pref", "denomination": pref}, started)

    history = state.get("messages") or []
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
    transcript += f"\nuser: {state.get('user_message', '')}"
    out = await achat_json_model(get_prompt("denom_infer", "system"), transcript, DenomInferResult)

    denom = out.denomination
    if out.confidence < 0.6:
        denom = Denomination.NONE
    state["denomination"] = denom.value
    return audit(
        state,
        "denom_resolver",
        {"source": "inferred", "denomination": denom.value, "confidence": out.confidence},
        started,
    )
