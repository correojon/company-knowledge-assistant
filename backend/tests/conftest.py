"""Shared fixtures: every test runs offline, on the fake provider, in its own data dir.

See research.md R11. In-process FastAPI ``TestClient`` traffic uses no sockets, so the
network guard does not affect it.
"""

import os
import socket
from collections.abc import Iterator
from pathlib import Path

import pytest

# Every key in contracts/configuration.md. Values inherited from the shell or from a
# developer's environment must never reach a test.
CONFIG_KEYS = (
    "CONFIG_FILE_LOADED",
    "LLM_PROVIDER",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OPENAI_COMPAT_BASE_URL",
    "OPENAI_COMPAT_API_KEY",
    "OPENAI_COMPAT_MODEL",
    "LLM_TIMEOUT_SECONDS",
    "EMBEDDING_MODEL",
    "DATA_DIR",
    "BACKEND_PORT",
    "FRONTEND_PORT",
    "API_PROXY_TARGET",
)


class NetworkBlockedError(RuntimeError):
    """Raised when a test tries to open a network connection.

    Deliberately not an ``OSError``: HTTP clients turn ``OSError`` into a connection
    error, which provider code reports as "unavailable". That would hide the attempt
    instead of failing the test.
    """


def _format_address(address: object) -> str:
    if isinstance(address, tuple) and len(address) >= 2:
        return f"{address[0]}:{address[1]}"
    return repr(address)


def _blocked(address: object) -> NetworkBlockedError:
    target = _format_address(address)
    return NetworkBlockedError(
        f"network access is blocked in tests: attempted connection to {target}. "
        "Use FakeProvider or httpx.MockTransport instead."
    )


@pytest.fixture(autouse=True)
def _offline_test_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[None]:
    def guarded_connect(_sock: socket.socket, address: object) -> None:
        raise _blocked(address)

    def guarded_create_connection(address: object, *_: object, **__: object) -> None:
        raise _blocked(address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)

    # pydantic-settings matches names case-insensitively: remove every casing of a key.
    wanted = set(CONFIG_KEYS)
    for name in list(os.environ):
        if name.upper() in wanted:
            monkeypatch.delenv(name)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    yield
