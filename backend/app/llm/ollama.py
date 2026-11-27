"""A provider backed by a local Ollama server.

See contracts/llm-provider.md and research.md R7.
"""

from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal

import httpx

from app.llm.types import Availability, ChatMessage, Completion

CHECK_TIMEOUT_SECONDS = 3.0


class OllamaProvider:
    name: Literal["ollama"] = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, timeout=timeout, transport=self._transport
        )

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> Completion:
        raise NotImplementedError("OllamaProvider.complete arrives in T029")

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]:
        raise NotImplementedError("OllamaProvider.stream arrives in T029")

    async def check(self) -> Availability:
        """List local models with ``GET /api/tags``. Never generates, never raises."""
        try:
            async with self._client(CHECK_TIMEOUT_SECONDS) as client:
                response = await client.get("/api/tags")
        except httpx.TransportError:
            return _unavailable(f"cannot reach {self.base_url} (is Ollama running?)")
        except Exception as exc:  # check() must never raise (contract rule 3).
            return _unavailable(f"availability check failed ({type(exc).__name__})")

        if not response.is_success:
            return _unavailable(f"unexpected response (HTTP {response.status_code})")

        names = _model_names(response)
        if names is None:
            return _unavailable("unexpected response (malformed /api/tags body)")
        if self.model in names or f"{self.model}:latest" in names:
            return Availability(status="available")
        return _unavailable(
            f"model '{self.model}' not found; run: ollama pull {self.model}"
        )


def _unavailable(reason: str) -> Availability:
    return Availability(status="unavailable", reason=reason)


def _model_names(response: httpx.Response) -> set[str] | None:
    """Every listed model's ``name``, or ``None`` if the body has the wrong shape."""
    try:
        body: Any = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict) or not isinstance(body.get("models"), list):
        return None
    return {
        entry["name"]
        for entry in body["models"]
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
