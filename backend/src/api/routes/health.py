from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.postgres import get_session
from core.settings import get_settings
from schemas.health import DbPingResponse, HealthResponse, PlatformReadinessResponse
from services.platform_service import get_health_response, get_platform_readiness

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return get_health_response()


@router.get("/readiness", response_model=PlatformReadinessResponse)
async def platform_readiness() -> PlatformReadinessResponse:
    return get_platform_readiness()


@router.get("/health/db", response_model=DbPingResponse)
async def db_ping(session: Annotated[AsyncSession, Depends(get_session)]) -> DbPingResponse:
    settings = get_settings()
    # Extract host from DATABASE_URL for display (hide credentials)
    try:
        host = settings.database_url.split("@")[-1].split("/")[0]
    except Exception:
        host = "unknown"

    try:
        await session.execute(text("SELECT 1"))
        return DbPingResponse(status="ok", database_url_host=host)
    except Exception as exc:
        return DbPingResponse(status="error", database_url_host=host, detail=str(exc))
