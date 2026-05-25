from fastapi import APIRouter

from schemas.profile import ProfileTypeCatalog
from services.profile_service import get_supported_profile_types

router = APIRouter()


@router.get("/types", response_model=ProfileTypeCatalog)
async def list_profile_types() -> ProfileTypeCatalog:
    return get_supported_profile_types()
