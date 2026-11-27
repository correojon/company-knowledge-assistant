"""SQLite store: data directory, sqlite-vec engine, migrations, vector check (R8)."""

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

import alembic.command
import sqlite_vec
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlmodel import create_engine

# backend/app/db.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
MIGRATIONS_DIR = BACKEND_DIR / "migrations"

# Three 4-d vectors and a query whose nearest neighbour must be rowid 2.
_SMOKE_VECTORS = {1: "[1, 0, 0, 0]", 2: "[0, 1, 0, 0]", 3: "[0, 0, 1, 0]"}
_SMOKE_QUERY = "[0.1, 0.9, 0, 0]"
_SMOKE_EXPECTED_ROWID = 2


class StartupError(RuntimeError):
    """A startup step failed; the message is the one-line reason shown to the user."""


def _reason(exc: BaseException) -> str:
    """One line describing ``exc``, without SQLAlchemy's SQL echo and links."""
    if isinstance(exc, DBAPIError) and exc.orig is not None:
        exc = exc.orig
    lines = str(exc).strip().splitlines()
    return lines[0] if lines else type(exc).__name__


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


@dataclass(frozen=True)
class Migration:
    """The schema revision before and after ``migrate``; ``before`` is None if empty."""

    before: str | None
    revision: str

    @property
    def summary(self) -> str:
        """One line for the startup log."""
        if self.before == self.revision:
            return f"Database schema already at head ({self.revision})."
        if self.before is None:
            return f"Database created at schema revision {self.revision}."
        return f"Database migrated from {self.before} to {self.revision}."


def migrate(engine: Engine) -> Migration:
    """Bring the store up to the head revision and report where it started and ended."""
    cfg = Config(str(ALEMBIC_INI))
    # ConfigParser interpolates "%", so escape it in case the checkout path has one.
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR).replace("%", "%%"))
    try:
        with engine.begin() as conn:
            before = MigrationContext.configure(conn).get_current_revision()
            cfg.attributes["connection"] = conn
            alembic.command.upgrade(cfg, "head")
            revision = MigrationContext.configure(conn).get_current_revision()
    except Exception as exc:
        raise StartupError(f"migration failed: {_reason(exc)}") from exc
    if revision is None:
        raise StartupError("migration failed: no schema revision after upgrade")
    return Migration(before=before, revision=revision)


def vector_smoke_check(engine: Engine) -> str:
    """Run a KNN query on a throwaway vec0 table and return sqlite-vec's version."""
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT vec_version()")).scalar_one()
            conn.execute(
                text(
                    "CREATE VIRTUAL TABLE temp.vec_smoke USING vec0(embedding float[4])"
                )
            )
            try:
                for rowid, vector in _SMOKE_VECTORS.items():
                    conn.execute(
                        text(
                            "INSERT INTO temp.vec_smoke (rowid, embedding) "
                            "VALUES (:rowid, :vector)"
                        ),
                        {"rowid": rowid, "vector": vector},
                    )
                nearest = conn.execute(
                    text(
                        "SELECT rowid FROM temp.vec_smoke "
                        "WHERE embedding MATCH :query AND k = 1"
                    ),
                    {"query": _SMOKE_QUERY},
                ).scalar_one()
            finally:
                # Commit the drop: a rollback would restore the table on this pooled
                # connection, and the next check would fail on CREATE.
                conn.execute(text("DROP TABLE IF EXISTS temp.vec_smoke"))
                conn.commit()
    except Exception as exc:
        raise StartupError(f"vector search unavailable: {_reason(exc)}") from exc
    if nearest != _SMOKE_EXPECTED_ROWID:
        raise StartupError(
            "vector search unavailable: KNN query returned row "
            f"{nearest}, expected {_SMOKE_EXPECTED_ROWID}"
        )
    if not version:
        raise StartupError("vector search unavailable: vec_version() returned nothing")
    return str(version)
