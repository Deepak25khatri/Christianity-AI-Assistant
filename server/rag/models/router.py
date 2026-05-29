from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from rag.models.enums import Denomination, Intent


class RouterResult(BaseModel):
    intent: Intent = Intent.THEOLOGICAL_Q

    @field_validator("intent", mode="before")
    @classmethod
    def _coerce_intent(cls, value: object) -> Intent:
        if isinstance(value, Intent):
            return value
        try:
            return Intent(str(value))
        except ValueError:
            return Intent.THEOLOGICAL_Q


class DenomInferResult(BaseModel):
    denomination: Denomination = Denomination.NONE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("denomination", mode="before")
    @classmethod
    def _coerce_denomination(cls, value: object) -> Denomination:
        if isinstance(value, Denomination):
            return value
        try:
            return Denomination(str(value))
        except ValueError:
            return Denomination.NONE
