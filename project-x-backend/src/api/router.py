from fastapi import APIRouter

from api.routes.assets import router as assets_router
from api.routes.health import router as health_router
from api.routes.profiles import router as profiles_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/system", tags=["system"])
api_router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])
