"""The interface every language-model call goes through (contracts/llm-provider.md)."""

import asyncio
import time
from collections.abc import AsyncIterator, Callable, Sequence
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


class SupportsCheck(Protocol):
    async def check(self) -> Availability: ...


class AvailabilityCache:
    """Reuse a provider's last ``check()`` result until it is ``ttl_seconds`` old.

    Unavailable results are cached too, so a down provider is probed at most once per
    TTL (SC-008). The lock lets concurrent callers share one probe.
    """

    def __init__(
        self,
        provider: SupportsCheck,
        ttl_seconds: float = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._provider = provider
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = asyncio.Lock()
        self._cached: Availability | None = None
        self._probed_at = 0.0

    async def get(self) -> Availability:
        async with self._lock:
            cached = self._cached
            if cached is not None and self._clock() - self._probed_at < self._ttl:
                return cached
            result = await self._provider.check()
            self._cached, self._probed_at = result, self._clock()
            return result
