from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_account_context
from connectors.postgres import get_session
from schemas.auth import (
    AccountResponse,
    AuthSessionResponse,
    AuthTokensResponse,
    LogoutRequest,
    LogoutResponse,
    OtpRequest,
    OtpSessionResponse,
    OtpVerifyRequest,
    RefreshTokenRequest,
    SignupCompleteRequest,
    SignupVerificationResponse,
)
from schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PaginatedResponse
from services.auth_service import (
    AuthenticatedAccountContext,
    AuthRequestContext,
    build_account_response,
    complete_signup,
    list_account_sessions,
    logout_account,
    refresh_session,
    request_otp,
    revoke_account_session,
    verify_otp,
)

router = APIRouter()


@router.post(
    "/otp/request",
    response_model=OtpSessionResponse,
)
async def otp_request(
    payload: OtpRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OtpSessionResponse:
    return await request_otp(session, payload, _build_request_context(request))


@router.post(
    "/otp/verify",
    response_model=SignupVerificationResponse | AuthTokensResponse,
)
async def otp_verify(
    payload: OtpVerifyRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SignupVerificationResponse | AuthTokensResponse:
    return await verify_otp(session, payload, _build_request_context(request))


@router.post(
    "/signup/complete",
    response_model=AuthTokensResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup_complete(
    payload: SignupCompleteRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthTokensResponse:
    return await complete_signup(session, payload, _build_request_context(request))


@router.post("/refresh", response_model=AuthTokensResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthTokensResponse:
    return await refresh_session(session, payload.refresh_token, _build_request_context(request))


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    payload: Annotated[LogoutRequest, Body(default_factory=LogoutRequest)],
) -> LogoutResponse:
    return await logout_account(session, auth_context, payload.refresh_token)


@router.get("/me", response_model=AccountResponse)
async def get_current_account(
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
) -> AccountResponse:
    return build_account_response(auth_context.account, auth_context.profile_id)


@router.get("/sessions", response_model=PaginatedResponse[AuthSessionResponse])
async def list_sessions(
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[AuthSessionResponse]:
    return await list_account_sessions(session, auth_context, limit=limit, offset=offset)


@router.post("/sessions/{session_id}/revoke", response_model=LogoutResponse)
async def revoke_session(
    session_id: str,
    auth_context: Annotated[AuthenticatedAccountContext, Depends(get_current_account_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LogoutResponse:
    return await revoke_account_session(session, auth_context, session_id)


def _build_request_context(request: Request) -> AuthRequestContext:
    return AuthRequestContext(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        device_name=request.headers.get("x-device-name"),
    )
