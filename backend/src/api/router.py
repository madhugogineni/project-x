from fastapi import APIRouter

from api.routes.assets import router as assets_router
from api.routes.auth import router as auth_router
from api.routes.documents import router as documents_router
from api.routes.health import router as health_router
from api.routes.nominees import router as nominees_router
from api.routes.profiles import router as profiles_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/system", tags=["system"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
api_router.include_router(assets_router, prefix="/assets", tags=["assets"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(nominees_router, prefix="/nominees", tags=["nominees"])
