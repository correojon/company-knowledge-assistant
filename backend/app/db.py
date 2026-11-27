"""SQLite store: data directory, engine with sqlite-vec loaded, migrations (R8)."""

import sqlite3
import uuid
from pathlib import Path

import alembic.command
import sqlite_vec
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, event
from sqlmodel import create_engine

# backend/app/db.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
MIGRATIONS_DIR = BACKEND_DIR / "migrations"


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


def migrate(engine: Engine) -> str:
    """Bring the store up to the head revision and return the revision it is now at."""
    cfg = Config(str(ALEMBIC_INI))
    # ConfigParser interpolates "%", so escape it in case the checkout path has one.
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR).replace("%", "%%"))
    try:
        with engine.begin() as conn:
            cfg.attributes["connection"] = conn
            alembic.command.upgrade(cfg, "head")
            revision = MigrationContext.configure(conn).get_current_revision()
    except Exception as exc:
        raise StartupError(f"migration failed: {exc}") from exc
    if revision is None:
        raise StartupError("migration failed: no schema revision after upgrade")
    return revision
