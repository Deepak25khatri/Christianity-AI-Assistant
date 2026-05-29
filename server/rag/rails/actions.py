"""NeMo Guardrails custom actions for input/output safety checks."""
from __future__ import annotations

import re
from typing import Any

from nemoguardrails.actions import action
from pydantic import BaseModel, Field

from rag.llm import achat_json_model, amoderate
from rag.models.enums import SafetyLabel
from rag.models.guards import InputGuardResult, OutputGuardResult
from rag.prompt_loader import get_prompt

INJECTION_PATTERNS = [
    r"ignore (all )?previous (instructions|prompts|rules)",
    r"disregard (the )?(system|above)",
    r"you are now (a|an)",
    r"pretend you are",
    r"act as (?:if you are )?(god|jesus|the holy spirit|the bible)",
    r"reveal (your )?(system|hidden) prompt",
    r"\bDAN\b",
    r"role[- ]?play as",
]
_INJ_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


class InputGuardLLM(BaseModel):
    label: str = "safe"
    reason: str | None = None


class OutputGuardLLM(BaseModel):
    block: bool = False
    reason: str | None = None


def _label_from_str(raw: str) -> SafetyLabel:
    try:
        return SafetyLabel(raw)
    except ValueError:
        return SafetyLabel.SAFE


@action(is_system_action=True, name="check_input_safety")
async def check_input_safety(message: str = "") -> dict[str, Any]:
    mod = await amoderate(message)
    if mod.flagged:
        result = InputGuardResult.blocked_result(
            SafetyLabel.POLICY_VIOLATION,
            f"moderation: {[k for k, v in mod.categories.items() if v]}",
            via="nemo_moderation",
        )
        return result.model_dump()

    if _INJ_RE.search(message):
        result = InputGuardResult.blocked_result(
            SafetyLabel.ADVERSARIAL,
            "prompt-injection pattern matched",
            via="nemo_regex",
        )
        return result.model_dump()

    cls = await achat_json_model(
        get_prompt("input_guard", "system"),
        message,
        InputGuardLLM,
    )
    label = _label_from_str(cls.label)
    blocked = label != SafetyLabel.SAFE
    result = InputGuardResult(
        label=label,
        reason=cls.reason,
        blocked=blocked,
        via="nemo_llm",
    )
    return result.model_dump()


@action(is_system_action=True, name="check_output_safety")
async def check_output_safety(draft: str = "") -> dict[str, Any]:
    mod = await amoderate(draft)
    if mod.flagged:
        return OutputGuardResult(
            block=True,
            reason="post-output moderation flagged",
            via="nemo_moderation",
        ).model_dump()

    cls = await achat_json_model(
        get_prompt("output_guard", "system"),
        draft,
        OutputGuardLLM,
    )
    return OutputGuardResult(
        block=bool(cls.block),
        reason=cls.reason,
        via="nemo_llm",
    ).model_dump()
