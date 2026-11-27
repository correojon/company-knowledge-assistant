"""Application factory and startup sequence (data-model.md "Startup")."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy import Engine

from app.api.health import router as health_router
from app.config import Settings
from app.db import create_db_engine, migrate, prepare_data_dir, vector_smoke_check
from app.llm.base import AvailabilityCache, LLMProvider
from app.llm.factory import build_provider


@dataclass(frozen=True)
class AppState:
    """What a successful startup produced; held on ``app.state.app_state``."""

    engine: Engine
    schema_revision: str
    migration_summary: str
    vec_version: str
    provider: LLMProvider
    availability: AvailabilityCache


def startup(settings: Settings, provider: LLMProvider | None = None) -> AppState:
    """Prepare the store and the provider, or raise ``StartupError``.

    The provider is not contacted here: availability is checked lazily (FR-012).
    """
    prepare_data_dir(settings.data_dir)
    engine = create_db_engine(settings.database_path)
    try:
        migration = migrate(engine)
        vec_version = vector_smoke_check(engine)
    except BaseException:
        engine.dispose()
        raise
    if provider is None:
        provider = build_provider(settings)
    return AppState(
        engine=engine,
        schema_revision=migration.revision,
        migration_summary=migration.summary,
        vec_version=vec_version,
        provider=provider,
        availability=AvailabilityCache(provider),
    )


def create_app(
    settings: Settings,
    *,
    state: AppState | None = None,
    provider: LLMProvider | None = None,
) -> FastAPI:
    """Build the app. Without ``state``, startup runs in the lifespan with ``provider``.

    A ``state`` from an earlier ``startup`` call is used as is, and its owner disposes
    of its engine.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = state is None
        app_state = startup(settings, provider) if state is None else state
        app.state.app_state = app_state
        try:
            yield
        finally:
            if owned:
                app_state.engine.dispose()

    app = FastAPI(title="Knowledge Assistant", lifespan=lifespan)
    app.include_router(health_router)
    return app
