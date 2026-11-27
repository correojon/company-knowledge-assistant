"""SQLite store: data directory, engine with sqlite-vec loaded (research.md R8)."""

import sqlite3
import uuid
from pathlib import Path

import sqlite_vec
from sqlalchemy import Engine, event
from sqlmodel import create_engine


class StartupError(RuntimeError):
    """A startup step failed; the message is the one-line reason shown to the user."""


def prepare_data_dir(path: Path) -> None:
    """Create ``path`` if needed and prove it is writable with a probe file."""
    probe = path / f".write-probe-{uuid.uuid4().hex}"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as exc:
        raise StartupError(f"data directory '{path}' is not writable") from exc


def _on_connect(dbapi_connection: sqlite3.Connection, _record: object) -> None:
    dbapi_connection.enable_load_extension(True)
    try:
        sqlite_vec.load(dbapi_connection)
    finally:
        dbapi_connection.enable_load_extension(False)
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_db_engine(database_path: Path) -> Engine:
    """Engine whose every connection has sqlite-vec loaded, WAL and foreign keys on."""
    engine = create_engine(f"sqlite:///{database_path}")
    event.listen(engine, "connect", _on_connect)
    return engine
