from fastapi import APIRouter

from schemas.asset import AssetBlueprintResponse
from services.asset_service import get_asset_blueprint

router = APIRouter()


@router.get("/blueprint", response_model=AssetBlueprintResponse)
async def asset_blueprint() -> AssetBlueprintResponse:
    return get_asset_blueprint()
