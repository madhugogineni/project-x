from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_account_context
from connectors.postgres import get_session
from schemas.nominee import (
    NomineeCreateRequest,
    NomineeResponse,
    NomineeScopeReplaceRequest,
    NomineeScopeResponse,
    NomineeUpdateRequest,
    NomineeVisibilityUpdateRequest,
)
from schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PaginatedResponse
from services.auth_service import AuthenticatedAccountContext
from services.nominee_service import (
    create_nominee,
    get_nominee,
    get_nominee_scope,
    list_nominees,
    remove_nominee,
    replace_nominee_scope,
    update_nominee,
    update_nominee_visibility,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[NomineeResponse])
async def nominee_list(
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[NomineeResponse]:
    return await list_nominees(session, auth_context, limit=limit, offset=offset)


@router.post("", response_model=NomineeResponse, status_code=status.HTTP_201_CREATED)
async def nominee_create(
    payload: NomineeCreateRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NomineeResponse:
    return await create_nominee(session, auth_context, payload)


@router.get("/{nominee_id}", response_model=NomineeResponse)
async def nominee_detail(
    nominee_id: str,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NomineeResponse:
    return await get_nominee(session, auth_context, nominee_id)


@router.patch("/{nominee_id}", response_model=NomineeResponse)
async def nominee_update(
    nominee_id: str,
    payload: NomineeUpdateRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NomineeResponse:
    return await update_nominee(session, auth_context, nominee_id, payload)


@router.delete("/{nominee_id}", response_model=NomineeResponse)
async def nominee_delete(
    nominee_id: str,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NomineeResponse:
    return await remove_nominee(session, auth_context, nominee_id)


@router.get("/{nominee_id}/scope", response_model=PaginatedResponse[NomineeScopeResponse])
async def nominee_scope_list(
    nominee_id: str,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[NomineeScopeResponse]:
    return await get_nominee_scope(session, auth_context, nominee_id, limit=limit, offset=offset)


@router.put("/{nominee_id}/scope", response_model=list[NomineeScopeResponse])
async def nominee_scope_replace(
    nominee_id: str,
    payload: NomineeScopeReplaceRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[NomineeScopeResponse]:
    return await replace_nominee_scope(session, auth_context, nominee_id, payload)


@router.put("/{nominee_id}/visibility", response_model=list[NomineeScopeResponse])
async def nominee_visibility_update(
    nominee_id: str,
    payload: NomineeVisibilityUpdateRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[NomineeScopeResponse]:
    return await update_nominee_visibility(session, auth_context, nominee_id, payload)
