"""A deterministic provider with canned replies, for tests and offline runs (FR-015)."""

import re
from collections.abc import AsyncIterator, Sequence
from typing import Literal

from app.llm.types import Availability, ChatMessage, Completion

DEFAULT_REPLY = "This is a canned reply from the fake provider."

# A word with the whitespace after it, or whitespace alone at the start.
_CHUNK = re.compile(r"\S+\s*|\s+")


class FakeProvider:
    name: Literal["fake"] = "fake"
    model: str = "fake"

    def __init__(self, replies: Sequence[str] | None = None) -> None:
        if replies is not None and len(replies) == 0:
            raise ValueError("replies must not be empty; pass None for the default")
        self._replies = list(replies) if replies is not None else [DEFAULT_REPLY]
        self._next = 0
        self.calls: list[list[ChatMessage]] = []

    def _take(self, messages: Sequence[ChatMessage]) -> str:
        self.calls.append(list(messages))
        reply = self._replies[self._next]
        self._next = (self._next + 1) % len(self._replies)
        return reply

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> Completion:
        return Completion(text=self._take(messages), model=self.model, provider="fake")

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        # Take the reply now, not on first iteration, so call order decides the cycle.
        return _iterate(_CHUNK.findall(self._take(messages)))

    async def check(self) -> Availability:
        return Availability(status="available")


async def _iterate(chunks: list[str]) -> AsyncIterator[str]:
    for chunk in chunks:
        yield chunk
