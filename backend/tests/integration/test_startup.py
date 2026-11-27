"""Startup: data directory, engine, migrations, vector check and app lifespan (R8)."""

import os
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from pathlib import Path

import alembic.command
import pytest
import sqlite_vec
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.db import (
    Migration,
    StartupError,
    create_db_engine,
    migrate,
    prepare_data_dir,
    vector_smoke_check,
)
from app.llm.base import AvailabilityCache
from app.llm.fake import FakeProvider
from app.main import AppState

AppFactory = Callable[..., FastAPI]

skip_if_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores directory permissions",
)


def test_prepare_data_dir_creates_missing_dir(tmp_path: Path) -> None:
    data_dir = tmp_path / "nested" / "data"

    prepare_data_dir(data_dir)

    assert data_dir.is_dir()
    assert list(data_dir.iterdir()) == []


@skip_if_root
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
    migration = migrate(engine)

    assert migration.before is None
    assert migration.revision == "0001_baseline"
    assert migration.summary == "Database created at schema revision 0001_baseline."
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
        migration = migrate(restarted)
    finally:
        restarted.dispose()

    assert migration.before == migration.revision == "0001_baseline"
    assert migration.summary == "Database schema already at head (0001_baseline)."
    assert database_path.stat().st_ino == inode_before
    with closing(sqlite3.connect(database_path)) as conn:
        assert conn.execute("SELECT value FROM sentinel").fetchall() == [("kept",)]


def test_migration_summary_names_both_revisions() -> None:
    migration = Migration(before="0001_baseline", revision="0002_documents")

    expected = "Database migrated from 0001_baseline to 0002_documents."
    assert migration.summary == expected


def test_migration_failure_stops_startup(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_upgrade(*_: object, **__: object) -> None:
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(alembic.command, "upgrade", broken_upgrade)

    with pytest.raises(StartupError) as excinfo:
        migrate(engine)

    assert str(excinfo.value) == "migration failed: disk on fire"


def test_vector_smoke_check_returns_version(engine: Engine) -> None:
    version = vector_smoke_check(engine)

    assert isinstance(version, str)
    assert version


def test_vector_load_failure_stops_startup(
    database_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_load(_conn: object) -> None:
        raise RuntimeError("extension missing")

    monkeypatch.setattr(sqlite_vec, "load", broken_load)
    engine = create_db_engine(database_path)
    try:
        with pytest.raises(StartupError) as excinfo:
            vector_smoke_check(engine)
    finally:
        engine.dispose()

    assert str(excinfo.value) == "vector search unavailable: extension missing"


def test_vector_smoke_check_leaves_nothing_behind(
    engine: Engine, database_path: Path
) -> None:
    # Same pooled connection twice: the temp table must really be dropped.
    vector_smoke_check(engine)
    assert vector_smoke_check(engine)

    with closing(sqlite3.connect(database_path)) as conn:
        names = conn.execute("SELECT name FROM sqlite_master").fetchall()
    assert ("vec_smoke",) not in names


def test_startup_creates_store_and_passes_smoke(
    app_factory: AppFactory, tmp_path: Path
) -> None:
    app = app_factory()

    with TestClient(app):
        assert (tmp_path / "data" / "knowledge.sqlite3").is_file()
        state = app.state.app_state
        assert isinstance(state, AppState)
        assert state.schema_revision == "0001_baseline"
        assert state.vec_version
        assert isinstance(state.provider, FakeProvider)
        assert isinstance(state.availability, AvailabilityCache)


@skip_if_root
def test_startup_failure_propagates(app_factory: AppFactory, tmp_path: Path) -> None:
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(0o500)
    app = app_factory(data_dir=readonly / "data")
    try:
        with pytest.raises(StartupError, match="is not writable"), TestClient(app):
            pass
    finally:
        readonly.chmod(0o700)


def test_given_state_skips_startup(
    app_factory: AppFactory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app import main
    from app.config import Settings

    state = main.startup(
        Settings(_env_file=None, llm_provider="fake", data_dir=tmp_path / "data")
    )

    def no_startup(*_: object, **__: object) -> AppState:
        raise AssertionError("startup must not run when state is given")

    monkeypatch.setattr(main, "startup", no_startup)
    app = app_factory(state=state)

    with TestClient(app):
        assert app.state.app_state is state
    state.engine.dispose()
