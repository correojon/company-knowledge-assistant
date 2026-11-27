"""Alembic environment.

At app startup, ``app.db.migrate`` passes its connection in
``config.attributes["connection"]``. From the ``alembic`` CLI, the engine is built from
the app's Settings. ``fileConfig`` is deliberately not called, so the app's logging is
left alone.
"""

from alembic import context
from sqlalchemy.engine import Connection
from sqlmodel import SQLModel

from app.config import load_settings
from app.db import create_db_engine

target_metadata = SQLModel.metadata


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        run_migrations(connection)
        return

    engine = create_db_engine(load_settings().database_path)
    try:
        with engine.begin() as conn:
            run_migrations(conn)
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise SystemExit("offline (--sql) migrations are not supported")
run_migrations_online()
