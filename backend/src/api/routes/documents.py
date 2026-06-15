from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_account_context
from connectors.postgres import get_session
from schemas.asset import (
    DocumentDownloadUrlResponse,
    DocumentMetadataResponse,
    DocumentUploadCompleteRequest,
    DocumentUploadInitiateRequest,
    DocumentUploadInitiateResponse,
)
from schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PaginatedResponse
from services.asset_service import (
    complete_document_upload,
    delete_document,
    get_document_download_url,
    get_document_metadata,
    initiate_document_upload,
    list_asset_documents,
)
from services.auth_service import AuthenticatedAccountContext

router = APIRouter()


@router.get(
    "/assets/{asset_id}/documents",
    response_model=PaginatedResponse[DocumentMetadataResponse],
)
async def asset_document_list(
    asset_id: str,
    profile_id: Annotated[str, Query()],
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    primary_profile_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[DocumentMetadataResponse]:
    return await list_asset_documents(
        session,
        auth_context,
        asset_id=asset_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/assets/{asset_id}/documents/initiate-upload",
    response_model=DocumentUploadInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def asset_document_initiate_upload(
    asset_id: str,
    payload: DocumentUploadInitiateRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentUploadInitiateResponse:
    return await initiate_document_upload(
        session,
        auth_context,
        asset_id=asset_id,
        payload=payload,
    )


@router.post(
    "/assets/{asset_id}/documents/complete-upload",
    response_model=DocumentMetadataResponse,
)
async def asset_document_complete_upload(
    asset_id: str,
    payload: DocumentUploadCompleteRequest,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentMetadataResponse:
    return await complete_document_upload(
        session,
        auth_context,
        asset_id=asset_id,
        document_id=payload.document_id,
        payload=payload,
    )


@router.get("/documents/{document_id}", response_model=DocumentMetadataResponse)
async def document_detail(
    document_id: str,
    profile_id: Annotated[str, Query()],
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    primary_profile_id: Annotated[str | None, Query()] = None,
) -> DocumentMetadataResponse:
    return await get_document_metadata(
        session,
        auth_context,
        document_id=document_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
    )


@router.post(
    "/documents/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
)
async def document_download_url(
    document_id: str,
    profile_id: Annotated[str, Query()],
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    primary_profile_id: Annotated[str | None, Query()] = None,
) -> DocumentDownloadUrlResponse:
    return await get_document_download_url(
        session,
        auth_context,
        document_id=document_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
    )


@router.delete("/documents/{document_id}", response_model=DocumentMetadataResponse)
async def document_delete(
    document_id: str,
    profile_id: Annotated[str, Query()],
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    primary_profile_id: Annotated[str | None, Query()] = None,
) -> DocumentMetadataResponse:
    return await delete_document(
        session,
        auth_context,
        document_id=document_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
    )
