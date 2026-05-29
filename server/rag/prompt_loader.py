"""Load prompt templates from YAML files under rag/prompts/."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_SECTION_FILES = {
    "input_guard": "guards",
    "output_guard": "guards",
    "router": "guards",
    "denom_infer": "guards",
    "generator": "generator",
    "image_sanitize": "image",
    "image_policy": "image",
}


@lru_cache(maxsize=32)
def _load_yaml(name: str) -> dict[str, Any]:
    path = PROMPTS_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_prompt(*keys: str) -> str:
    """Navigate nested YAML keys, e.g. get_prompt('generator', 'system')."""
    if len(keys) < 2:
        raise KeyError("Use get_prompt('section', 'field', ...)")

    section = keys[0]
    yaml_stem = _SECTION_FILES.get(section, section)
    data = _load_yaml(f"{yaml_stem}.yaml")
    node: Any = data.get(section, data if section == yaml_stem else {})
    for key in keys[1:]:
        if not isinstance(node, dict):
            raise KeyError(f"Prompt not found: {'.'.join(keys)}")
        node = node.get(key)
    if isinstance(node, str):
        return node.strip()
    raise KeyError(f"Prompt not found: {'.'.join(keys)}")


def format_prompt(*keys: str, **kwargs: Any) -> str:
    return get_prompt(*keys).format(**kwargs)


def get_refusal(key: str) -> str:
    data = _load_yaml("refusals.yaml")
    return (data.get(key) or "").strip()


def refusal_templates() -> dict[str, str]:
    return _load_yaml("refusals.yaml")
