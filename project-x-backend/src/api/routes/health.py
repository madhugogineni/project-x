from fastapi import APIRouter

from schemas.health import HealthResponse, PlatformReadinessResponse
from services.platform_service import get_health_response, get_platform_readiness

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return get_health_response()


@router.get("/readiness", response_model=PlatformReadinessResponse)
async def platform_readiness() -> PlatformReadinessResponse:
    return get_platform_readiness()
