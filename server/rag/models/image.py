from __future__ import annotations

from pydantic import BaseModel


class ImageSanitizeResult(BaseModel):
    prompt: str = ""
    reason: str | None = None

    @property
    def blocked(self) -> bool:
        p = (self.prompt or "").strip().upper()
        return not p or p.startswith("BLOCK")


class ImagePolicyResult(BaseModel):
    allow: bool = False
    reason: str | None = None
