"""Startup building blocks: data directory, engine, migrations, vector check (R8)."""

import os
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db import StartupError, create_db_engine, prepare_data_dir


def test_prepare_data_dir_creates_missing_dir(tmp_path: Path) -> None:
    data_dir = tmp_path / "nested" / "data"

    prepare_data_dir(data_dir)

    assert data_dir.is_dir()
    assert list(data_dir.iterdir()) == []


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores directory permissions",
)
def test_unwritable_data_dir_fails(tmp_path: Path) -> None:
    data_dir = tmp_path / "readonly"
    data_dir.mkdir()
    data_dir.chmod(0o500)
    try:
        with pytest.raises(StartupError) as excinfo:
            prepare_data_dir(data_dir)
    finally:
        data_dir.chmod(0o700)

    assert str(excinfo.value) == f"data directory '{data_dir}' is not writable"


def test_engine_connection_has_vec_and_pragmas(tmp_path: Path) -> None:
    engine = create_db_engine(tmp_path / "knowledge.sqlite3")
    try:
        with engine.connect() as conn:
            vec_version = conn.execute(text("SELECT vec_version()")).scalar_one()
            journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar_one()
            foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar_one()
    finally:
        engine.dispose()

    assert vec_version
    assert journal_mode == "wal"
    assert foreign_keys == 1
