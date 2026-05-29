"""NeMo Guardrails integration for input/output safety."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from nemoguardrails import LLMRails, RailsConfig

from rag.models.guards import InputGuardResult, OutputGuardResult
from rag.rails.actions import check_input_safety, check_output_safety

log = logging.getLogger(__name__)

RAILS_DIR = Path(__file__).resolve().parent / "rails"

_rails: LLMRails | None = None


def _ensure_openai_key() -> None:
    from app.config import get_settings

    key = get_settings().openai_api_key
    if key:
        os.environ.setdefault("OPENAI_API_KEY", key)


def get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        _ensure_openai_key()
        config = RailsConfig.from_path(str(RAILS_DIR))
        _rails = LLMRails(config)
        _rails.register_action(check_input_safety, name="check_input_safety")
        _rails.register_action(check_output_safety, name="check_output_safety")
        log.info("NeMo Guardrails initialized from %s", RAILS_DIR)
    return _rails


async def check_input(message: str) -> InputGuardResult:
    raw = await check_input_safety(message=message)
    return InputGuardResult.model_validate(raw)


async def check_output(draft: str) -> OutputGuardResult:
    raw = await check_output_safety(draft=draft)
    return OutputGuardResult.model_validate(raw)
