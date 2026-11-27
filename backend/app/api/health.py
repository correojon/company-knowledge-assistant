"""``GET /api/health``: backend, store and language-model status (FR-003).

Wire models follow data-model.md "HealthReport" and contracts/openapi-health.yaml.
"""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import AwareDatetime, BaseModel

from app import __version__
from app.llm.types import ProviderName


class DatabaseStatus(BaseModel):
    status: Literal["ok"]
    schema_revision: str
    vector_search: Literal["ok"]
    vector_search_version: str


class LLMStatus(BaseModel):
    provider: ProviderName
    model: str
    status: Literal["available", "unavailable"]
    reason: str | None
    checked_at: AwareDatetime


class HealthReport(BaseModel):
    status: Literal["ok"]
    version: str
    database: DatabaseStatus
    llm: LLMStatus


router = APIRouter(prefix="/api")


@router.get(
    "/health",
    operation_id="getHealth",
    summary="Backend, data store and language model status",
)
async def get_health(request: Request) -> HealthReport:
    """Always 200 while serving. The llm section comes from the cached check."""
    state = request.app.state.app_state
    availability = await state.availability.get()
    return HealthReport(
        status="ok",
        version=__version__,
        database=DatabaseStatus(
            status="ok",
            schema_revision=state.schema_revision,
            vector_search="ok",
            vector_search_version=state.vec_version,
        ),
        llm=LLMStatus(
            provider=state.provider.name,
            model=state.provider.model,
            status=availability.status,
            reason=availability.reason,
            checked_at=availability.checked_at,
        ),
    )
