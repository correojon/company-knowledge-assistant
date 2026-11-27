# Contract: LLMProvider (internal interface)

Module: `backend/app/llm/`. Every later feature that calls a language model MUST go through this interface. Tests MUST use `FakeProvider` (Constitution IV, FR-014).

```python
class LLMProvider(Protocol):
    name: Literal["fake", "ollama", "openai_compat"]
    model: str

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> Completion: ...

    def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> AsyncIterator[str]: ...   # yields text chunks in order; joined == full reply

    async def check(self) -> Availability: ...   # MUST NOT generate text

def build_provider(settings: Settings) -> LLMProvider: ...
```

## Behavioural rules

1. `complete` and `stream` raise `LLMProviderError(reason)` on transport errors, timeouts (`llm_timeout_seconds`), non-2xx responses or malformed bodies. `reason` is a single human-readable line and MUST NOT include the API key or the `Authorization` header.
2. `"".join(chunks from stream(m))` MUST equal `complete(m).text` for `FakeProvider`. For real providers, the two are only equivalent in meaning.
3. `check()` never raises. It returns `Availability(status="unavailable", reason=...)` instead. Its timeout is 3 seconds.
4. `check()` sends no generation requests:
   - `OllamaProvider` uses `GET /api/tags`.
   - `OpenAICompatProvider` uses `GET {base}/models`.

   Model matching rules are in [research.md R7](../research.md#r7-availability-check-and-cache-fr-012-clarification-q3-sc-008).
5. `build_provider` raises nothing for reachability. It only maps an already-validated setting to a class, so configuration errors are caught earlier by `Settings` (FR-011).

## FakeProvider

```python
FakeProvider(replies: Sequence[str] | None = None)
```

- With no `replies`, it uses the single default reply `"This is a canned reply from the fake provider."`.
- Each call to `complete` or `stream` returns the next reply in order and cycles back to the start, so the same sequence of calls always gives the same outputs (FR-015).
- `stream` yields the reply split on whitespace boundaries, keeping the whitespace, so the chunks join back to the exact reply.
- `calls: list[list[ChatMessage]]` records the received messages for assertions.
- It performs no I/O. `check()` always returns `available`.

## Wire formats (implementations)

| Provider | Complete | Stream | Check |
|---|---|---|---|
| `ollama` | `POST {OLLAMA_BASE_URL}/api/chat` with `{"model", "messages", "stream": false, "options": {"temperature", "num_predict"}}`; reply text in `message.content` | Same request with `"stream": true`; NDJSON lines, `message.content` per line until `"done": true` | `GET /api/tags` |
| `openai_compat` | `POST {OPENAI_COMPAT_BASE_URL}/chat/completions` with `{"model", "messages", "temperature", "max_tokens"}` and `Authorization: Bearer <key>`; text in `choices[0].message.content` | Same request with `"stream": true`; SSE `data:` lines, `choices[0].delta.content`, ending with `data: [DONE]` | `GET {base}/models` |
