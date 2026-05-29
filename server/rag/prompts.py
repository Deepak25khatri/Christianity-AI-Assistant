"""Backward-compatible re-exports; prefer rag.prompt_loader directly."""
from __future__ import annotations

from rag.prompt_loader import format_prompt, get_prompt, get_refusal, refusal_templates

GENERATOR_SYSTEM = get_prompt("generator", "system")
GENERATOR_COMPARISON_INSTRUCTIONS = get_prompt("generator", "comparison_instructions")
GENERATOR_STANDARD_INSTRUCTIONS = get_prompt("generator", "standard_instructions")
GENERATOR_REGENERATION_NOTE = get_prompt("generator", "regeneration_note")
INPUT_GUARD_SYSTEM = get_prompt("input_guard", "system")
ROUTER_SYSTEM = get_prompt("router", "system")
DENOM_INFER_SYSTEM = get_prompt("denom_infer", "system")
OUTPUT_GUARD_SYSTEM = get_prompt("output_guard", "system")
IMAGE_PROMPT_SANITIZER_SYSTEM = get_prompt("image_sanitize", "system")
IMAGE_POLICY_SYSTEM = get_prompt("image_policy", "system")
REFUSAL_TEMPLATES = refusal_templates()

__all__ = [
    "GENERATOR_SYSTEM",
    "GENERATOR_COMPARISON_INSTRUCTIONS",
    "GENERATOR_STANDARD_INSTRUCTIONS",
    "GENERATOR_REGENERATION_NOTE",
    "INPUT_GUARD_SYSTEM",
    "ROUTER_SYSTEM",
    "DENOM_INFER_SYSTEM",
    "OUTPUT_GUARD_SYSTEM",
    "IMAGE_PROMPT_SANITIZER_SYSTEM",
    "IMAGE_POLICY_SYSTEM",
    "REFUSAL_TEMPLATES",
    "format_prompt",
    "get_prompt",
    "get_refusal",
]
