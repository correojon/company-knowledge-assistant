"""Startup building blocks: data directory, engine, migrations, vector check (R8)."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import alembic.command
import pytest
from sqlalchemy import Engine, text

from app.db import StartupError, create_db_engine, migrate, prepare_data_dir


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


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "knowledge.sqlite3"


@pytest.fixture
def engine(database_path: Path) -> Iterator[Engine]:
    engine = create_db_engine(database_path)
    yield engine
    engine.dispose()


def test_migrate_fresh_store_to_head(engine: Engine, database_path: Path) -> None:
    revision = migrate(engine)

    assert revision == "0001_baseline"
    with closing(sqlite3.connect(database_path)) as conn:
        rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    assert rows == [("0001_baseline",)]


def test_restart_reuses_store(engine: Engine, database_path: Path) -> None:
    migrate(engine)
    with closing(sqlite3.connect(database_path)) as conn, conn:
        conn.execute("CREATE TABLE sentinel (value TEXT)")
        conn.execute("INSERT INTO sentinel VALUES ('kept')")
    inode_before = database_path.stat().st_ino
    engine.dispose()

    restarted = create_db_engine(database_path)
    try:
        revision = migrate(restarted)
    finally:
        restarted.dispose()

    assert revision == "0001_baseline"
    assert database_path.stat().st_ino == inode_before
    with closing(sqlite3.connect(database_path)) as conn:
        assert conn.execute("SELECT value FROM sentinel").fetchall() == [("kept",)]


def test_migration_failure_stops_startup(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_upgrade(*_: object, **__: object) -> None:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(alembic.command, "upgrade", broken_upgrade)

    with pytest.raises(StartupError) as excinfo:
        migrate(engine)

    assert str(excinfo.value) == "migration failed: disk on fire"
