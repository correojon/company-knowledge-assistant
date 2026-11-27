"""The interface every language-model call goes through (contracts/llm-provider.md)."""

from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from app.llm.types import Availability, ChatMessage, Completion, ProviderName


class LLMProvider(Protocol):
    name: ProviderName
    model: str

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> Completion:
        """Return the full reply, or raise ``LLMProviderError``."""
        ...

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        """Yield the reply in order as text chunks, or raise ``LLMProviderError``."""
        ...

    async def check(self) -> Availability:
        """Report whether the provider can serve requests. Never raises or generates."""
        ...
