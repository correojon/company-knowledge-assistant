"""OllamaProvider talks to Ollama's HTTP API (contracts/llm-provider.md, R7).

Every test drives the provider through ``httpx.MockTransport``: nothing leaves
the process.
"""

from collections.abc import Callable

import httpx
import pytest

from app.llm.ollama import OllamaProvider

BASE_URL = "http://ollama.test:11434"
MODEL = "llama3.2:3b"

Handler = Callable[[httpx.Request], httpx.Response]


class Recorder:
    """A MockTransport handler that records every request it receives."""

    def __init__(self, respond: Handler) -> None:
        self._respond = respond
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._respond(request)


def tags(*names: str) -> Handler:
    def respond(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": n} for n in names]})

    return respond


def raising(exc: Exception) -> Handler:
    def respond(_: httpx.Request) -> httpx.Response:
        raise exc

    return respond


def make(
    handler: Handler, *, model: str = MODEL, base_url: str = BASE_URL
) -> OllamaProvider:
    return OllamaProvider(
        base_url=base_url,
        model=model,
        timeout_seconds=120,
        transport=httpx.MockTransport(handler),
    )


def test_identifies_itself() -> None:
    provider = make(tags())
    assert provider.name == "ollama"
    assert provider.model == MODEL


async def test_check_sends_only_get_api_tags() -> None:
    recorder = Recorder(tags(MODEL))
    await make(recorder).check()

    assert [(r.method, r.url.path) for r in recorder.requests] == [("GET", "/api/tags")]
    assert all(r.method != "POST" for r in recorder.requests)
    assert recorder.requests[0].url.host == "ollama.test"


async def test_check_handles_a_trailing_slash_on_the_base_url() -> None:
    recorder = Recorder(tags(MODEL))
    result = await make(recorder, base_url=BASE_URL + "/").check()

    assert result.status == "available"
    assert recorder.requests[0].url.path == "/api/tags"


async def test_exact_model_name_is_available() -> None:
    result = await make(tags("other:1b", MODEL)).check()
    assert result.status == "available"
    assert result.reason is None


async def test_model_without_tag_matches_name_plus_latest() -> None:
    result = await make(tags("mistral:latest"), model="mistral").check()
    assert result.status == "available"


async def test_a_different_tag_does_not_match() -> None:
    provider = make(tags("llama3.2:1b", "llama3.2:latest"), model="llama3.2:3b")
    result = await provider.check()
    assert result.status == "unavailable"


async def test_missing_model_says_how_to_pull_it() -> None:
    result = await make(tags("other:1b")).check()
    assert result.status == "unavailable"
    assert result.reason == f"model '{MODEL}' not found; run: ollama pull {MODEL}"


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("[Errno 111] Connection refused"),
        httpx.ConnectTimeout("timed out"),
        httpx.ReadTimeout("timed out"),
    ],
    ids=["refused", "connect-timeout", "read-timeout"],
)
async def test_unreachable_server(exc: Exception) -> None:
    result = await make(raising(exc)).check()
    assert result.status == "unavailable"
    assert result.reason == f"cannot reach {BASE_URL} (is Ollama running?)"


async def test_unreachable_reason_omits_a_trailing_slash() -> None:
    provider = make(raising(httpx.ConnectError("refused")), base_url=BASE_URL + "/")
    result = await provider.check()
    assert result.reason == f"cannot reach {BASE_URL} (is Ollama running?)"


async def test_http_503_is_an_unexpected_response() -> None:
    result = await make(lambda _: httpx.Response(503, text="loading")).check()
    assert result.status == "unavailable"
    assert result.reason == "unexpected response (HTTP 503)"


@pytest.mark.parametrize(
    "respond",
    [
        lambda _: httpx.Response(200, text="not json"),
        lambda _: httpx.Response(200, json=["a list"]),
        lambda _: httpx.Response(200, json={"models": "nope"}),
        lambda _: httpx.Response(200, json={"models": [{"no_name": 1}, 42]}),
        lambda _: httpx.Response(404),
        raising(httpx.RemoteProtocolError("garbled")),
        raising(RuntimeError("anything at all")),
    ],
    ids=[
        "not-json",
        "not-object",
        "models-not-list",
        "bad-entries",
        "404",
        "protocol",
        "other",
    ],
)
async def test_check_never_raises(respond: Handler) -> None:
    result = await make(respond).check()
    assert result.status == "unavailable"
    assert result.reason
    assert "\n" not in result.reason


async def test_probe_timeout_is_three_seconds() -> None:
    recorder = Recorder(tags(MODEL))
    await make(recorder).check()

    timeout = recorder.requests[0].extensions["timeout"]
    assert timeout == {"connect": 3.0, "read": 3.0, "write": 3.0, "pool": 3.0}


async def test_complete_and_stream_are_not_implemented_yet() -> None:
    provider = make(tags(MODEL))
    with pytest.raises(NotImplementedError):
        await provider.complete([])
    with pytest.raises(NotImplementedError):
        provider.stream([])
