from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from rag.models.enums import SafetyLabel


class ModerationResult(BaseModel):
    flagged: bool = False
    categories: dict[str, bool] = Field(default_factory=dict)
    error: str | None = None


class InputGuardResult(BaseModel):
    label: SafetyLabel = SafetyLabel.SAFE
    reason: str | None = None
    blocked: bool = False
    via: str | None = None  # moderation | regex | nemo | llm

    @field_validator("label", mode="before")
    @classmethod
    def _coerce_label(cls, value: object) -> SafetyLabel:
        if isinstance(value, SafetyLabel):
            return value
        try:
            return SafetyLabel(str(value))
        except ValueError:
            return SafetyLabel.SAFE

    @classmethod
    def blocked_result(cls, label: SafetyLabel, reason: str, via: str) -> InputGuardResult:
        return cls(label=label, reason=reason, blocked=True, via=via)


class OutputGuardResult(BaseModel):
    block: bool = False
    reason: str | None = None
    via: str | None = None
