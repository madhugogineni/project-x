from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_account_context
from connectors.postgres import get_session
from schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PaginatedResponse
from schemas.profile import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileTypeCatalog,
    ProfileUpsertResponse,
)
from services.auth_service import AuthenticatedAccountContext
from services.profile_service import (
    create_advisor_profile,
    get_profile,
    get_supported_profile_types,
    list_profiles,
    validate_public_profile_creation_request,
)

router = APIRouter()


@router.get("/types", response_model=ProfileTypeCatalog)
async def list_profile_types() -> ProfileTypeCatalog:
    return get_supported_profile_types()


@router.get("", response_model=PaginatedResponse[ProfileResponse])
async def profile_list(
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[ProfileResponse]:
    return await list_profiles(session, auth_context, limit=limit, offset=offset)


@router.post("", response_model=ProfileUpsertResponse)
async def create_profile(
    payload: ProfileCreateRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileUpsertResponse:
    validate_public_profile_creation_request(payload.profile_type)
    return await create_advisor_profile(session, auth_context)


@router.get("/{profile_id}", response_model=ProfileResponse)
async def profile_detail(
    profile_id: str,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileResponse:
    return await get_profile(session, auth_context, profile_id)
