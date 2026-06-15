from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_account_context
from connectors.postgres import get_session
from schemas.asset import (
    AssetBlueprintResponse,
    AssetCreateRequest,
    AssetListItemResponse,
    AssetResponse,
    AssetTypeCatalogResponse,
    AssetUpdateRequest,
)
from schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PaginatedResponse
from services.asset_service import (
    create_asset,
    delete_asset,
    get_asset,
    get_asset_blueprint,
    get_asset_types,
    list_assets,
    update_asset,
)
from services.auth_service import AuthenticatedAccountContext

router = APIRouter()


@router.get("/types", response_model=AssetTypeCatalogResponse)
async def asset_type_catalog() -> AssetTypeCatalogResponse:
    return get_asset_types()


@router.get("/blueprint", response_model=AssetBlueprintResponse)
async def asset_blueprint() -> AssetBlueprintResponse:
    return get_asset_blueprint()


@router.get("", response_model=PaginatedResponse[AssetListItemResponse])
async def asset_list(
    profile_id: Annotated[str, Query()],
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    primary_profile_id: Annotated[str | None, Query()] = None,
    container_type: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = True,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[AssetListItemResponse]:
    return await list_assets(
        session,
        auth_context,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        container_type=container_type,
        is_active=is_active,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def asset_create(
    payload: AssetCreateRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetResponse:
    return await create_asset(session, auth_context, payload)


@router.get("/{asset_id}", response_model=AssetResponse)
async def asset_detail(
    asset_id: str,
    profile_id: Annotated[str, Query()],
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    primary_profile_id: Annotated[str | None, Query()] = None,
) -> AssetResponse:
    return await get_asset(
        session,
        auth_context,
        asset_id=asset_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
    )


@router.patch("/{asset_id}", response_model=AssetResponse)
async def asset_update(
    asset_id: str,
    payload: AssetUpdateRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssetResponse:
    return await update_asset(
        session,
        auth_context,
        asset_id=asset_id,
        payload=payload,
    )


@router.delete("/{asset_id}", response_model=AssetResponse)
async def asset_delete(
    asset_id: str,
    profile_id: Annotated[str, Query()],
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    primary_profile_id: Annotated[str | None, Query()] = None,
) -> AssetResponse:
    return await delete_asset(
        session,
        auth_context,
        asset_id=asset_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
    )
