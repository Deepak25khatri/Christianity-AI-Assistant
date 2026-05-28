"""LangGraph wiring for the Christianity assistant.

Topology (see plan):

    input_guard -> [refusal | router]
    router -> [image_sanitize | denom_resolver]
    denom_resolver -> retriever -> generator -> verse_validator
    verse_validator -> [generator (one corrective loop) | output_guard]
    output_guard -> [refusal | finalize]
    image_sanitize -> image_policy -> image_generate -> finalize
"""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from rag.nodes.finalize import finalize
from rag.nodes.generator import generator
from rag.nodes.guards import input_guard, output_guard, refusal_node
from rag.nodes.image import image_generate, image_policy, image_sanitize
from rag.nodes.retriever import retriever
from rag.nodes.router import denom_resolver, router
from rag.nodes.verse_validator import verse_validator
from rag.state import GraphState

log = logging.getLogger(__name__)


def _route_after_input_guard(state: GraphState) -> Literal["refusal", "router"]:
    return "refusal" if state.get("blocked_input") else "router"


def _route_after_router(state: GraphState) -> Literal["image_sanitize", "denom_resolver"]:
    return "image_sanitize" if state.get("intent") == "image_request" else "denom_resolver"


def _route_after_validator(state: GraphState) -> Literal["generator", "output_guard"]:
    if state.get("validator_notes") and int(state.get("regenerate_attempts") or 0) <= 1:
        return "generator"
    return "output_guard"


def _route_after_output_guard(state: GraphState) -> Literal["refusal", "finalize"]:
    return "refusal" if state.get("output_blocked") else "finalize"


def build_graph(checkpointer=None):
    g: StateGraph = StateGraph(GraphState)

    g.add_node("input_guard", input_guard)
    g.add_node("router", router)
    g.add_node("denom_resolver", denom_resolver)
    g.add_node("retriever", retriever)
    g.add_node("generator", generator)
    g.add_node("verse_validator", verse_validator)
    g.add_node("output_guard", output_guard)
    g.add_node("refusal", refusal_node)
    g.add_node("finalize", finalize)
    g.add_node("image_sanitize", image_sanitize)
    g.add_node("image_policy", image_policy)
    g.add_node("image_generate", image_generate)

    g.set_entry_point("input_guard")
    g.add_conditional_edges("input_guard", _route_after_input_guard,
                            {"refusal": "refusal", "router": "router"})
    g.add_conditional_edges("router", _route_after_router,
                            {"image_sanitize": "image_sanitize",
                             "denom_resolver": "denom_resolver"})

    g.add_edge("denom_resolver", "retriever")
    g.add_edge("retriever", "generator")
    g.add_edge("generator", "verse_validator")
    g.add_conditional_edges("verse_validator", _route_after_validator,
                            {"generator": "generator", "output_guard": "output_guard"})
    g.add_conditional_edges("output_guard", _route_after_output_guard,
                            {"refusal": "refusal", "finalize": "finalize"})

    g.add_edge("image_sanitize", "image_policy")
    g.add_edge("image_policy", "image_generate")
    g.add_edge("image_generate", "finalize")

    g.add_edge("refusal", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer) if checkpointer else g.compile()


_compiled = None


def get_graph(checkpointer=None):
    global _compiled
    if _compiled is None:
        _compiled = build_graph(checkpointer=checkpointer)
    return _compiled
