import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_configs import (
    OTP_COOLDOWN_MINUTES,
    OTP_MAX_ATTEMPTS,
    OTP_MAX_RESENDS,
    get_otp_flow_config,
)
from core.security import (
    TokenClaims,
    TokenValidationError,
    create_jwt,
    decode_jwt,
    encrypt_sensitive_value,
    generate_numeric_otp,
    hash_secret,
    utc_now,
    verify_secret,
)
from core.settings import get_settings
from db.models import (
    Account,
    AccountAddress,
    AccountAuthToken,
    AccountInactivityState,
    AccountOtpSession,
    AccountPan,
    Profile,
    ProfileType,
)
from schemas.auth import (
    AccountResponse,
    AuthSessionResponse,
    AuthTokensResponse,
    LogoutResponse,
    OtpRequest,
    OtpSessionResponse,
    OtpVerifyRequest,
    SignupCompleteRequest,
    SignupVerificationResponse,
)
from schemas.pagination import PaginatedResponse, build_paginated_response
from services.nominee_service import autolink_nominee_records_for_account
from services.profile_service import ensure_default_profiles

TOKEN_TYPE_ACCESS = "ACCESS"
TOKEN_TYPE_REFRESH = "REFRESH"
TOKEN_TYPE_SIGNUP_VERIFIED = "SIGNUP_VERIFIED"


@dataclass(frozen=True)
class AuthRequestContext:
    ip_address: str | None
    user_agent: str | None
    device_name: str | None


@dataclass(frozen=True)
class AuthenticatedAccountContext:
    account: Account
    profile_id: str | None
    claims: TokenClaims
    session_id: str | None = None


def build_account_response(account: Account, primary_profile_id: str | None) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        email=account.email,
        phone=account.phone,
        full_name=account.full_name,
        email_verified=account.email_verified,
        phone_verified=account.phone_verified,
        status=account.status,
        primary_profile_id=primary_profile_id,
    )


async def request_otp(
    session: AsyncSession,
    payload: OtpRequest,
    request_context: AuthRequestContext,
) -> OtpSessionResponse:
    flow_config = get_otp_flow_config(payload.flow)
    await _validate_otp_flow_prerequisites(session, payload.phone, flow_config)
    await _acquire_otp_flow_lock(session, payload.phone, payload.flow)

    now = utc_now()
    otp_session = await _get_latest_pending_otp_session(
        session=session,
        phone=payload.phone,
        flow=payload.flow,
    )
    if otp_session is None:
        return await _create_otp_session(
            session=session,
            phone=payload.phone,
            flow=payload.flow,
            request_context=request_context,
        )

    if otp_session.cooldown_until is not None and now < otp_session.cooldown_until:
        raise _cooldown_error(otp_session.cooldown_until)

    if otp_session.resend_count >= otp_session.max_resends:
        # Explicit cooldown expired → allow fresh request
        if otp_session.cooldown_until is not None and now >= otp_session.cooldown_until:
            otp_session.consumed_at = now
            await session.flush()
            return await _create_otp_session(
                session=session,
                phone=payload.phone,
                flow=payload.flow,
                request_context=request_context,
            )

        # OTP itself has expired naturally (user waited without retrying) → allow fresh request
        if now >= otp_session.expires_at:
            otp_session.consumed_at = now
            await session.flush()
            return await _create_otp_session(
                session=session,
                phone=payload.phone,
                flow=payload.flow,
                request_context=request_context,
            )

        # Resends exhausted and OTP still valid → impose cooldown
        otp_session.cooldown_until = now + timedelta(minutes=OTP_COOLDOWN_MINUTES)
        await session.flush()
        raise _cooldown_error(otp_session.cooldown_until)

    if now >= otp_session.expires_at:
        otp_session.consumed_at = now
        await session.flush()
        return await _create_otp_session(
            session=session,
            phone=payload.phone,
            flow=payload.flow,
            request_context=request_context,
        )

    return await _resend_otp_session(
        session=session,
        otp_session=otp_session,
        request_context=request_context,
    )


async def verify_otp(
    session: AsyncSession,
    payload: OtpVerifyRequest,
    request_context: AuthRequestContext,
) -> SignupVerificationResponse | AuthTokensResponse:
    otp_session = await _verify_otp_session(
        session=session,
        otp_session_id=payload.otp_session_id,
        phone=payload.phone,
        otp=payload.otp,
        flow=payload.flow,
    )
    if payload.flow == "SIGNUP":
        return _build_signup_verification_response(otp_session)

    account = await _get_active_account_by_phone(session, otp_session.phone)
    now = utc_now()
    otp_session.consumed_at = now
    account.phone_verified = True
    account.last_login_at = now
    primary_profile, _nominee_profile = await _ensure_default_profiles(session, account)
    inactivity_state = await _ensure_inactivity_state(session, account.id, now)
    inactivity_state.last_active_at = now
    await session.flush()

    session_id = str(uuid4())
    return await _create_session_tokens(
        session=session,
        account=account,
        primary_profile_id=primary_profile.id,
        session_id=session_id,
        request_context=request_context,
    )


async def complete_signup(
    session: AsyncSession,
    payload: SignupCompleteRequest,
    request_context: AuthRequestContext,
) -> AuthTokensResponse:
    claims = _decode_token(
        payload.verified_signup_token,
        expected_token_type=TOKEN_TYPE_SIGNUP_VERIFIED,
    )
    otp_session = await _get_otp_session_for_completion(session, claims)

    phone_from_token = claims.extra_claims.get("phone")
    if not isinstance(phone_from_token, str) or otp_session.phone != phone_from_token:
        raise _bad_request_error("Signup verification proof is invalid.")

    await _ensure_account_is_unique(session, email=payload.email, phone=otp_session.phone)

    now = utc_now()
    session_id = str(uuid4())
    account = Account(
        email=payload.email,
        phone=otp_session.phone,
        phone_verified=True,
        email_verified=False,
        full_name=payload.full_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        last_login_at=now,
    )
    primary_profile = Profile(account=account, profile_type=ProfileType.PRIMARY)
    nominee_profile = Profile(account=account, profile_type=ProfileType.NOMINEE)
    inactivity_state = AccountInactivityState(account=account, last_active_at=now)
    pan = AccountPan(
        account=account,
        pan_number=encrypt_sensitive_value(
            payload.pan_number,
            get_settings().active_field_encryption_key,
        ),
        name_on_pan=payload.name_on_pan,
        is_verified=False,
        verification_source="SELF_DECLARED",
    )

    current_address = _build_address(account, "CURRENT", payload.current_address)
    permanent_source = (
        payload.current_address if payload.is_same_as_current else payload.permanent_address
    )
    if permanent_source is None:
        raise _bad_request_error("Permanent address is required.")
    permanent_address = _build_address(
        account,
        "PERMANENT",
        permanent_source,
        is_same_as_current=payload.is_same_as_current,
    )

    session.add_all(
        [
            account,
            primary_profile,
            nominee_profile,
            inactivity_state,
            pan,
            current_address,
            permanent_address,
        ]
    )

    otp_session.consumed_at = now
    try:
        await session.flush()
        await autolink_nominee_records_for_account(
            session,
            account=account,
            nominee_profile_id=nominee_profile.id,
            now=now,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict_error("An account with this email or phone already exists.") from exc

    return await _create_session_tokens(
        session=session,
        account=account,
        primary_profile_id=primary_profile.id,
        session_id=session_id,
        request_context=request_context,
    )


async def refresh_session(
    session: AsyncSession,
    refresh_token: str,
    request_context: AuthRequestContext,
) -> AuthTokensResponse:
    claims = _decode_token(refresh_token, expected_token_type=TOKEN_TYPE_REFRESH)
    token_record = await _get_token_record_for_update(session, claims.jti, TOKEN_TYPE_REFRESH)
    _assert_token_record_is_active(token_record, claims)

    account = await session.get(Account, claims.subject)
    if account is None or account.status != "ACTIVE" or account.deleted_at is not None:
        raise _unauthorized_error("This account is not allowed to sign in.")

    now = utc_now()
    token_record.revoked_at = now
    token_record.revoke_reason = "REFRESH_ROTATED"
    token_record.last_used_at = now

    primary_profile, _nominee_profile = await _ensure_default_profiles(session, account)
    inactivity_state = await _ensure_inactivity_state(session, account.id, now)
    inactivity_state.last_active_at = now
    await session.flush()

    return await _create_session_tokens(
        session=session,
        account=account,
        primary_profile_id=primary_profile.id,
        session_id=token_record.session_id,
        request_context=request_context,
    )


async def get_current_authenticated_account(
    session: AsyncSession,
    access_token: str,
) -> AuthenticatedAccountContext:
    claims = _decode_token(access_token, expected_token_type=TOKEN_TYPE_ACCESS)
    token_record = await _get_token_record_for_update(session, claims.jti, TOKEN_TYPE_ACCESS)
    _assert_token_record_is_active(token_record, claims)

    account = await session.get(Account, claims.subject)
    if account is None or account.status != "ACTIVE" or account.deleted_at is not None:
        raise _unauthorized_error("This account is not allowed to access this resource.")

    now = utc_now()
    token_record.last_used_at = now
    inactivity_state = await _ensure_inactivity_state(session, account.id, now)
    inactivity_state.last_active_at = now

    return AuthenticatedAccountContext(
        account=account,
        profile_id=token_record.active_profile_id or claims.profile_id,
        claims=claims,
        session_id=token_record.session_id,
    )


async def logout_account(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    refresh_token: str | None = None,
) -> LogoutResponse:
    now = utc_now()
    access_token_record = await _get_token_record_for_update(
        session,
        auth_context.claims.jti,
        TOKEN_TYPE_ACCESS,
    )
    revoked_access_token = _revoke_token_record(
        access_token_record,
        auth_context.claims,
        revoked_at=now,
        revoke_reason="LOGOUT",
    )

    revoked_refresh_token = False
    if refresh_token is not None:
        refresh_claims = _decode_token(refresh_token, expected_token_type=TOKEN_TYPE_REFRESH)
        if refresh_claims.subject != auth_context.account.id:
            raise _unauthorized_error("Token subject is invalid.")
        if refresh_claims.extra_claims.get("session_id") != access_token_record.session_id:
            raise _unauthorized_error("Token session is invalid.")

        refresh_token_record = await _get_token_record_for_update(
            session,
            refresh_claims.jti,
            TOKEN_TYPE_REFRESH,
        )
        revoked_refresh_token = _revoke_token_record(
            refresh_token_record,
            refresh_claims,
            revoked_at=now,
            revoke_reason="LOGOUT",
        )

    await session.flush()
    return LogoutResponse(
        revoked_access_token=revoked_access_token,
        revoked_refresh_token=revoked_refresh_token,
    )


async def list_account_sessions(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    limit: int,
    offset: int,
) -> PaginatedResponse[AuthSessionResponse]:
    now = utc_now()
    token_rows = (
        await session.scalars(
            select(AccountAuthToken)
            .where(
                AccountAuthToken.account_id == auth_context.account.id,
                AccountAuthToken.revoked_at.is_(None),
                AccountAuthToken.expires_at > now,
            )
            .order_by(AccountAuthToken.created_at.desc())
        )
    ).all()

    current_session_id = auth_context.session_id or auth_context.claims.extra_claims.get(
        "session_id"
    )
    grouped_sessions: dict[str, list[AccountAuthToken]] = {}
    for token_row in token_rows:
        grouped_sessions.setdefault(token_row.session_id, []).append(token_row)

    sessions: list[AuthSessionResponse] = []
    for session_id, rows in grouped_sessions.items():
        representative = max(
            rows,
            key=lambda row: row.last_used_at or row.created_at,
        )
        latest_active = max(
            (row.last_used_at or row.created_at for row in rows),
        )
        earliest_created = min(row.created_at for row in rows)
        sessions.append(
            AuthSessionResponse(
                id=session_id,
                session_id=session_id,
                jti=representative.jti,
                token_type=(
                    TOKEN_TYPE_ACCESS if session_id == current_session_id else TOKEN_TYPE_REFRESH
                ),
                device_name=representative.device_name,
                ip_address=representative.ip_address,
                user_agent=representative.user_agent,
                revoked_at=representative.revoked_at,
                last_used_at=latest_active,
                created_at=earliest_created,
                active_profile_id=representative.active_profile_id,
            )
        )

    sessions.sort(key=lambda item: item.last_used_at, reverse=True)
    total = len(sessions)
    return build_paginated_response(
        items=sessions[offset : offset + limit],
        total=total,
        limit=limit,
        offset=offset,
    )


async def revoke_account_session(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    session_id: str,
) -> LogoutResponse:
    current_session_id = auth_context.session_id or auth_context.claims.extra_claims.get(
        "session_id"
    )
    if session_id == current_session_id:
        raise _bad_request_error("Current session cannot be revoked from itself.")

    now = utc_now()
    token_rows = (
        await session.scalars(
            select(AccountAuthToken)
            .where(
                AccountAuthToken.account_id == auth_context.account.id,
                AccountAuthToken.session_id == session_id,
            )
            .with_for_update()
        )
    ).all()

    if not token_rows:
        raise _not_found_error("Session was not found.")

    revoked_any = False
    for token_row in token_rows:
        if token_row.revoked_at is None and token_row.expires_at > now:
            token_row.revoked_at = now
            token_row.revoke_reason = "FORCE_REVOKE"
            token_row.last_used_at = now
            revoked_any = True

    await session.flush()
    return LogoutResponse(
        revoked_access_token=revoked_any,
        revoked_refresh_token=revoked_any,
    )


async def _create_otp_session(
    *,
    session: AsyncSession,
    phone: str,
    flow: str,
    request_context: AuthRequestContext,
) -> OtpSessionResponse:
    settings = get_settings()
    now = utc_now()
    otp_code = _resolve_otp_code(settings)
    otp_session = AccountOtpSession(
        phone=phone,
        otp_hash=hash_secret(otp_code),
        purpose=flow,
        attempts=0,
        max_attempts=OTP_MAX_ATTEMPTS,
        resend_count=0,
        max_resends=OTP_MAX_RESENDS,
        expires_at=now + timedelta(minutes=settings.otp_ttl_minutes),
        last_sent_at=now,
        created_at=now,
        ip_address=request_context.ip_address,
        user_agent=request_context.user_agent,
    )
    session.add(otp_session)
    await session.flush()

    return _build_otp_session_response(otp_session)


async def _resend_otp_session(
    *,
    session: AsyncSession,
    otp_session: AccountOtpSession,
    request_context: AuthRequestContext,
) -> OtpSessionResponse:
    settings = get_settings()
    now = utc_now()
    otp_code = _resolve_otp_code(settings)
    otp_session.otp_hash = hash_secret(otp_code)
    otp_session.attempts = 0
    otp_session.resend_count += 1
    otp_session.expires_at = now + timedelta(minutes=settings.otp_ttl_minutes)
    otp_session.last_sent_at = now
    otp_session.cooldown_until = None
    otp_session.ip_address = request_context.ip_address
    otp_session.user_agent = request_context.user_agent
    await session.flush()

    return _build_otp_session_response(otp_session)


async def _verify_otp_session(
    *,
    session: AsyncSession,
    otp_session_id: str,
    phone: str,
    otp: str,
    flow: str,
) -> AccountOtpSession:
    otp_session = await session.scalar(
        select(AccountOtpSession)
        .where(
            AccountOtpSession.id == otp_session_id,
            AccountOtpSession.phone == phone,
            AccountOtpSession.purpose == flow,
        )
        .with_for_update()
    )
    if otp_session is None:
        raise _not_found_error("OTP session was not found.")
    if otp_session.consumed_at is not None:
        raise _bad_request_error("OTP session has already been used.")
    if otp_session.verified_at is not None and flow == "SIGNUP":
        if otp_session.verified_expires_at is None or utc_now() >= otp_session.verified_expires_at:
            raise _bad_request_error("OTP verification window has expired.")
        return otp_session
    if utc_now() >= otp_session.expires_at:
        raise _bad_request_error("OTP has expired.")
    if otp_session.attempts >= otp_session.max_attempts:
        raise _bad_request_error("OTP attempt limit exceeded.")

    if not verify_secret(otp, otp_session.otp_hash):
        otp_session.attempts += 1
        await session.flush()
        # Commit the attempt increment now so it persists even though we are
        # about to raise an HTTPException (which would otherwise trigger a
        # rollback in the session dependency and silently discard the update).
        await session.commit()
        if otp_session.attempts >= otp_session.max_attempts:
            raise _bad_request_error("OTP attempt limit exceeded.")
        raise _bad_request_error("OTP is invalid.")

    now = utc_now()
    otp_session.verified_at = now
    if flow == "SIGNUP":
        otp_session.verified_expires_at = now + timedelta(
            minutes=get_settings().verified_signup_ttl_minutes
        )
    await session.flush()
    return otp_session


def _build_signup_verification_response(
    otp_session: AccountOtpSession,
) -> SignupVerificationResponse:
    if otp_session.verified_expires_at is None:
        raise _bad_request_error("OTP session is not ready for signup completion.")

    settings = get_settings()
    verified_signup_token, claims = create_jwt(
        subject=otp_session.id,
        token_type=TOKEN_TYPE_SIGNUP_VERIFIED,
        secret_key=settings.jwt_secret_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=max(otp_session.verified_expires_at - utc_now(), timedelta(seconds=1)),
        additional_claims={"phone": otp_session.phone, "purpose": otp_session.purpose},
    )
    return SignupVerificationResponse(
        verified_signup_token=verified_signup_token,
        expires_at=claims.expires_at,
    )


def _build_otp_session_response(otp_session: AccountOtpSession) -> OtpSessionResponse:
    remaining_resends = max(0, otp_session.max_resends - otp_session.resend_count)
    attempts_remaining = max(0, otp_session.max_attempts - otp_session.attempts)
    return OtpSessionResponse(
        otp_session_id=otp_session.id,
        expires_at=otp_session.expires_at,
        flow=otp_session.purpose,
        resend_count=otp_session.resend_count,
        remaining_resends=remaining_resends,
        attempts_remaining=attempts_remaining,
        cooldown_until=otp_session.cooldown_until,
    )


async def _acquire_otp_flow_lock(session: AsyncSession, phone: str, flow: str) -> None:
    lock_key = _build_otp_flow_lock_key(phone, flow)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key},
    )


def _build_otp_flow_lock_key(phone: str, flow: str) -> int:
    digest = hashlib.blake2b(f"{phone}:{flow}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


def _cooldown_error(cooldown_until: datetime) -> HTTPException:
    retry_after_seconds = max(1, int((cooldown_until - utc_now()).total_seconds()))
    wait_suffix = "s" if retry_after_seconds != 1 else ""
    detail = (
        "A code was already sent. Please wait "
        f"{retry_after_seconds} second{wait_suffix} before requesting a new one."
    )
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(retry_after_seconds)},
    )


async def _validate_otp_flow_prerequisites(
    session: AsyncSession,
    phone: str,
    flow_config,
) -> None:
    if flow_config.requires_unique_phone:
        await _ensure_phone_is_available(session, phone)
    if flow_config.requires_existing_account:
        await _get_active_account_by_phone(session, phone)


async def _get_latest_pending_otp_session(
    *,
    session: AsyncSession,
    phone: str,
    flow: str,
) -> AccountOtpSession | None:
    now = utc_now()
    return await session.scalar(
        select(AccountOtpSession)
        .where(
            AccountOtpSession.phone == phone,
            AccountOtpSession.purpose == flow,
            AccountOtpSession.consumed_at.is_(None),
            AccountOtpSession.verified_at.is_(None),
            # Ignore sessions that are fully dead: expired with no active cooldown.
            # Sessions with an active cooldown must still be returned so the
            # cooldown can be enforced even after the OTP itself has expired.
            (AccountOtpSession.expires_at > now) | (AccountOtpSession.cooldown_until > now),
        )
        .order_by(AccountOtpSession.created_at.desc())
        .limit(1)
        .with_for_update()
    )


async def _get_otp_session_for_completion(
    session: AsyncSession,
    claims: TokenClaims,
) -> AccountOtpSession:
    purpose = claims.extra_claims.get("purpose")
    if purpose != "SIGNUP":
        raise _bad_request_error("Signup verification proof is invalid.")

    phone_from_claims = claims.extra_claims.get("phone")
    if not isinstance(phone_from_claims, str) or not phone_from_claims:
        raise _bad_request_error("Signup verification proof is invalid.")

    otp_session = await session.scalar(
        select(AccountOtpSession)
        .where(
            AccountOtpSession.id == claims.subject,
            AccountOtpSession.purpose == "SIGNUP",
            AccountOtpSession.phone == phone_from_claims,
        )
        .with_for_update()
    )
    if otp_session is None:
        raise _bad_request_error("Signup verification session was not found.")
    if otp_session.verified_at is None:
        raise _bad_request_error("OTP has not been verified.")
    if otp_session.verified_expires_at is None or utc_now() >= otp_session.verified_expires_at:
        raise _bad_request_error("Signup verification window has expired.")
    if otp_session.consumed_at is not None:
        raise _bad_request_error("Signup verification session has already been used.")
    return otp_session


def _build_address(
    account: Account,
    address_type: str,
    address_input,
    *,
    is_same_as_current: bool = False,
) -> AccountAddress:
    return AccountAddress(
        account=account,
        address_type=address_type,
        address_line_1=address_input.address_line_1,
        address_line_2=address_input.address_line_2,
        landmark=address_input.landmark,
        city=address_input.city,
        district=address_input.district,
        state=address_input.state,
        pincode=address_input.pincode,
        country=address_input.country,
        is_same_as_current=is_same_as_current,
    )


async def _ensure_phone_is_available(session: AsyncSession, phone: str) -> None:
    existing_phone = await session.scalar(
        select(Account.id).where(Account.phone == phone, Account.deleted_at.is_(None))
    )
    if existing_phone:
        raise _conflict_error("An account with this phone number already exists.")


async def _ensure_account_is_unique(session: AsyncSession, *, email: str, phone: str) -> None:
    existing_email = await session.scalar(
        select(Account.id).where(Account.email == email, Account.deleted_at.is_(None))
    )
    if existing_email:
        raise _conflict_error("An account with this email already exists.")

    existing_phone = await session.scalar(
        select(Account.id).where(Account.phone == phone, Account.deleted_at.is_(None))
    )
    if existing_phone:
        raise _conflict_error("An account with this phone number already exists.")


async def _get_active_account_by_phone(session: AsyncSession, phone: str) -> Account:
    account = await session.scalar(
        select(Account).where(
            Account.phone == phone,
            Account.status == "ACTIVE",
            Account.deleted_at.is_(None),
        )
    )
    if account is None:
        raise _not_found_error("No active account exists for this phone number.")
    return account


async def _ensure_default_profiles(
    session: AsyncSession,
    account: Account,
) -> tuple[Profile, Profile]:
    return await ensure_default_profiles(session, account.id)


async def _ensure_inactivity_state(
    session: AsyncSession,
    account_id: str,
    last_active_at: datetime,
) -> AccountInactivityState:
    inactivity_state = await session.scalar(
        select(AccountInactivityState).where(AccountInactivityState.account_id == account_id)
    )
    if inactivity_state is not None:
        return inactivity_state

    inactivity_state = AccountInactivityState(account_id=account_id, last_active_at=last_active_at)
    session.add(inactivity_state)
    await session.flush()
    return inactivity_state


async def _create_session_tokens(
    *,
    session: AsyncSession,
    account: Account,
    primary_profile_id: str | None,
    session_id: str,
    request_context: AuthRequestContext,
) -> AuthTokensResponse:
    settings = get_settings()
    now = utc_now()
    access_token, access_claims = create_jwt(
        subject=account.id,
        token_type=TOKEN_TYPE_ACCESS,
        secret_key=settings.jwt_secret_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=timedelta(minutes=settings.access_token_ttl_minutes),
        additional_claims={"profile_id": primary_profile_id, "session_id": session_id},
    )
    refresh_token, refresh_claims = create_jwt(
        subject=account.id,
        token_type=TOKEN_TYPE_REFRESH,
        secret_key=settings.jwt_secret_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=timedelta(days=settings.refresh_token_ttl_days),
        additional_claims={"profile_id": primary_profile_id, "session_id": session_id},
    )

    session.add_all(
        [
            AccountAuthToken(
                account_id=account.id,
                jti=access_claims.jti,
                session_id=session_id,
                token_type=TOKEN_TYPE_ACCESS,
                active_profile_id=primary_profile_id,
                device_name=request_context.device_name,
                ip_address=request_context.ip_address,
                user_agent=request_context.user_agent,
                expires_at=access_claims.expires_at,
                created_at=now,
                last_used_at=now,
            ),
            AccountAuthToken(
                account_id=account.id,
                jti=refresh_claims.jti,
                session_id=session_id,
                token_type=TOKEN_TYPE_REFRESH,
                active_profile_id=primary_profile_id,
                device_name=request_context.device_name,
                ip_address=request_context.ip_address,
                user_agent=request_context.user_agent,
                expires_at=refresh_claims.expires_at,
                created_at=now,
                last_used_at=now,
            ),
        ]
    )
    await session.flush()

    return AuthTokensResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_claims.expires_at,
        refresh_token_expires_at=refresh_claims.expires_at,
        account=build_account_response(account, primary_profile_id),
    )


async def _get_token_record_for_update(
    session: AsyncSession,
    jti: str,
    token_type: str,
) -> AccountAuthToken | None:
    return await session.scalar(
        select(AccountAuthToken)
        .where(
            AccountAuthToken.jti == jti,
            AccountAuthToken.token_type == token_type,
        )
        .with_for_update()
    )


async def _get_token_record(
    session: AsyncSession,
    jti: str,
    token_type: str,
) -> AccountAuthToken | None:
    return await session.scalar(
        select(AccountAuthToken).where(
            AccountAuthToken.jti == jti,
            AccountAuthToken.token_type == token_type,
        )
    )


def _assert_token_record_is_active(
    token_record: AccountAuthToken | None,
    claims: TokenClaims,
) -> None:
    if token_record is None:
        raise _unauthorized_error("Token is no longer valid.")
    if token_record.revoked_at is not None:
        raise _unauthorized_error("Token has been revoked.")
    if token_record.account_id != claims.subject:
        raise _unauthorized_error("Token subject is invalid.")
    if utc_now() >= token_record.expires_at:
        raise _unauthorized_error("Token has expired.")
    if utc_now() >= claims.expires_at:
        raise _unauthorized_error("Token has expired.")


def _revoke_token_record(
    token_record: AccountAuthToken | None,
    claims: TokenClaims,
    *,
    revoked_at: datetime,
    revoke_reason: str,
) -> bool:
    if token_record is None:
        return False
    if token_record.account_id != claims.subject:
        raise _unauthorized_error("Token subject is invalid.")
    if token_record.revoked_at is not None:
        return False
    if revoked_at >= token_record.expires_at or revoked_at >= claims.expires_at:
        return False

    token_record.revoked_at = revoked_at
    token_record.revoke_reason = revoke_reason
    token_record.last_used_at = revoked_at
    return True


def _decode_token(token: str, *, expected_token_type: str) -> TokenClaims:
    settings = get_settings()
    try:
        return decode_jwt(
            token,
            secret_key=settings.jwt_secret_key,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            expected_token_type=expected_token_type,
        )
    except TokenValidationError as exc:
        raise _unauthorized_error(str(exc)) from exc


def _resolve_otp_code(settings) -> str:
    if settings.environment == "local":
        return settings.local_otp
    return generate_numeric_otp(settings.otp_length)


def _bad_request_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _conflict_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _not_found_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _unauthorized_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
