"""``python -m app``: the notice, the startup sequence, then uvicorn (FR-008, US1-6)."""

import os
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI

from app import __main__ as entry


class UvicornSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, dict[str, Any]]] = []

    def __call__(self, app: Any, **kwargs: Any) -> None:
        self.calls.append((app, kwargs))


@pytest.fixture
def uvicorn_run(monkeypatch: pytest.MonkeyPatch) -> UvicornSpy:
    spy = UvicornSpy()
    monkeypatch.setattr(entry.uvicorn, "run", spy)
    return spy


def test_main_prints_notice_and_runs_uvicorn(
    uvicorn_run: UvicornSpy, capsys: pytest.CaptureFixture[str]
) -> None:
    entry.main()

    out = capsys.readouterr().out
    assert "Notice: no .env file found; using built-in defaults" in out
    assert len(uvicorn_run.calls) == 1
    app, kwargs = uvicorn_run.calls[0]
    assert isinstance(app, FastAPI)
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 8000


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root can write to read-only directories",
)
def test_main_startup_error_exits_1(
    uvicorn_run: UvicornSpy,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(0o500)
    monkeypatch.setenv("DATA_DIR", str(readonly / "data"))

    with pytest.raises(SystemExit) as exited:
        entry.main()

    assert exited.value.code == 1
    err = capsys.readouterr().err.strip().splitlines()
    assert err[-1].startswith("Startup failed: data directory")
    assert err[-1].endswith("is not writable.")
    assert uvicorn_run.calls == []
