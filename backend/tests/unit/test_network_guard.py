"""The autouse guard in conftest.py keeps every test off the network (US3-1, FR-014)."""

import os
import socket
from pathlib import Path

import httpx
import pytest

# Set at import time, before any fixture runs, to prove the guard clears inherited
# settings. The lowercase key matters: pydantic-settings reads environment variables
# case-insensitively.
os.environ["OPENAI_COMPAT_API_KEY"] = "sk-test-inherited-from-shell"
os.environ["openai_compat_model"] = "inherited-model"


def _assert_blocked(excinfo: pytest.ExceptionInfo[BaseException], target: str) -> None:
    assert excinfo.type.__name__ == "NetworkBlockedError"
    # Not an OSError: HTTP clients turn OSError into "connection failed", which would
    # hide the attempt behind a plausible "unavailable" result instead of failing.
    assert not issubclass(excinfo.type, OSError)
    assert target in str(excinfo.value)


def test_create_connection_is_blocked() -> None:
    with pytest.raises(RuntimeError) as excinfo:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    _assert_blocked(excinfo, "127.0.0.1:9")


def test_socket_connect_is_blocked() -> None:
    with socket.socket() as sock, pytest.raises(RuntimeError) as excinfo:
        sock.connect(("127.0.0.1", 9))
    _assert_blocked(excinfo, "127.0.0.1:9")


def test_socket_connect_ex_is_blocked() -> None:
    with socket.socket() as sock, pytest.raises(RuntimeError) as excinfo:
        sock.connect_ex(("127.0.0.1", 9))
    _assert_blocked(excinfo, "127.0.0.1:9")


def _leaf_exceptions(exc: BaseException) -> list[BaseException]:
    if isinstance(exc, BaseExceptionGroup):
        return [leaf for inner in exc.exceptions for leaf in _leaf_exceptions(inner)]
    return [exc]


async def test_async_httpx_attempt_fails_loudly() -> None:
    # The providers use httpx.AsyncClient. anyio may wrap the guard's error in an
    # ExceptionGroup, but it must never become an httpx error that provider code would
    # catch and report as "unavailable".
    async with httpx.AsyncClient() as client:
        with pytest.raises(BaseException) as excinfo:
            await client.get("http://127.0.0.1:9/")
    assert not isinstance(excinfo.value, httpx.HTTPError)
    leaves = _leaf_exceptions(excinfo.value)
    assert [type(leaf).__name__ for leaf in leaves] == ["NetworkBlockedError"]
    assert "127.0.0.1:9" in str(leaves[0])


def test_llm_provider_is_fake() -> None:
    assert os.environ["LLM_PROVIDER"] == "fake"


def test_data_dir_is_under_tmp_path(tmp_path: Path) -> None:
    assert Path(os.environ["DATA_DIR"]) == tmp_path / "data"


def test_inherited_settings_are_cleared() -> None:
    names = {name.upper() for name in os.environ}
    assert "OPENAI_COMPAT_API_KEY" not in names
    assert "OPENAI_COMPAT_MODEL" not in names
