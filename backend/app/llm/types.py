"""Value types shared by every LLM provider (data-model.md, "LLM types")."""

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

ProviderName = Literal["fake", "ollama", "openai_compat"]


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str


class Completion(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    model: str
    provider: ProviderName


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Availability(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["available", "unavailable"]
    reason: str | None = None
    checked_at: AwareDatetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.status == "unavailable" and not self.reason:
            raise ValueError("reason is required when status is 'unavailable'")
        if self.status == "available" and self.reason is not None:
            raise ValueError("reason must be null when status is 'available'")
        # Frozen model: bypass the setter to normalise the offset to UTC.
        object.__setattr__(self, "checked_at", self.checked_at.astimezone(UTC))
        return self


class LLMProviderError(Exception):
    """A generation request failed. ``reason`` is one line and never holds secrets."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
