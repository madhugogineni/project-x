import hashlib
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import utc_now
from db.models import Profile, ProfileAccess, ProfileType
from schemas.pagination import PaginatedResponse, build_paginated_response
from schemas.profile import (
    ProfileAccessRecord,
    ProfileAccessUpsertResult,
    ProfileResponse,
    ProfileTypeCatalog,
    ProfileUpsertResponse,
)


def get_supported_profile_types() -> ProfileTypeCatalog:
    return ProfileTypeCatalog(supported_types=[profile_type.value for profile_type in ProfileType])


async def list_profiles(
    session: AsyncSession,
    auth_context: Any,
    *,
    limit: int,
    offset: int,
) -> PaginatedResponse[ProfileResponse]:
    total = await session.scalar(
        select(func.count())
        .select_from(Profile)
        .where(Profile.account_id == auth_context.account.id)
    )
    profiles = (
        await session.scalars(
            select(Profile)
            .where(Profile.account_id == auth_context.account.id)
            .order_by(Profile.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return build_paginated_response(
        items=[ProfileResponse.model_validate(profile) for profile in profiles],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


async def get_profile(
    session: AsyncSession,
    auth_context: Any,
    profile_id: str,
) -> ProfileResponse:
    profile = await session.scalar(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.account_id == auth_context.account.id,
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return ProfileResponse.model_validate(profile)


async def ensure_profile(
    session: AsyncSession,
    account_id: str,
    profile_type: ProfileType,
) -> tuple[Profile, bool]:
    await _acquire_profile_lock(session, account_id, profile_type)
    profile = await session.scalar(
        select(Profile).where(
            Profile.account_id == account_id,
            Profile.profile_type == profile_type,
        )
    )
    if profile is not None:
        return profile, False

    profile = Profile(
        account_id=account_id,
        profile_type=profile_type,
        is_active=True,
    )
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile, True


async def ensure_default_profiles(
    session: AsyncSession,
    account_id: str,
) -> tuple[Profile, Profile]:
    primary_profile, _created = await ensure_profile(session, account_id, ProfileType.PRIMARY)
    nominee_profile, _created = await ensure_profile(session, account_id, ProfileType.NOMINEE)
    return primary_profile, nominee_profile


async def create_advisor_profile(
    session: AsyncSession,
    auth_context: Any,
) -> ProfileUpsertResponse:
    await ensure_default_profiles(session, auth_context.account.id)
    profile, created = await ensure_profile(
        session,
        auth_context.account.id,
        ProfileType.ADVISOR,
    )
    return ProfileUpsertResponse(
        profile=ProfileResponse.model_validate(profile),
        created=created,
    )


def validate_public_profile_creation_request(profile_type: str) -> ProfileType:
    normalized = ProfileType(profile_type)
    if normalized != ProfileType.ADVISOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only advisor profiles can be created through this endpoint.",
        )
    return normalized


async def list_profile_access_records(
    session: AsyncSession,
    *,
    accessor_profile_id: str | None = None,
    primary_profile_id: str | None = None,
    include_revoked: bool = False,
) -> list[ProfileAccess]:
    statement = select(ProfileAccess)
    if accessor_profile_id is not None:
        statement = statement.where(ProfileAccess.accessor_profile_id == accessor_profile_id)
    if primary_profile_id is not None:
        statement = statement.where(ProfileAccess.primary_profile_id == primary_profile_id)
    if not include_revoked:
        statement = statement.where(ProfileAccess.status == "ACTIVE")
    statement = statement.order_by(ProfileAccess.granted_at.desc())
    return (await session.scalars(statement)).all()


async def create_profile_access(
    session: AsyncSession,
    *,
    accessor_profile_id: str,
    primary_profile_id: str,
) -> ProfileAccessUpsertResult:
    accessor_profile, primary_profile = await _validate_profile_access_pair(
        session,
        accessor_profile_id=accessor_profile_id,
        primary_profile_id=primary_profile_id,
    )
    await _acquire_profile_access_lock(session, accessor_profile.id, primary_profile.id)

    access = await session.scalar(
        select(ProfileAccess).where(
            ProfileAccess.accessor_profile_id == accessor_profile.id,
            ProfileAccess.primary_profile_id == primary_profile.id,
        )
    )
    if access is not None:
        if access.status != "ACTIVE":
            access.status = "ACTIVE"
            access.granted_at = utc_now()
            access.revoked_at = None
            access.revoke_reason = None
            await session.flush()
        return ProfileAccessUpsertResult(
            access=ProfileAccessRecord.model_validate(access),
            created=False,
        )

    access = ProfileAccess(
        accessor_profile_id=accessor_profile.id,
        primary_profile_id=primary_profile.id,
        status="ACTIVE",
        granted_at=utc_now(),
    )
    session.add(access)
    await session.flush()
    await session.refresh(access)
    return ProfileAccessUpsertResult(
        access=ProfileAccessRecord.model_validate(access),
        created=True,
    )


async def revoke_profile_access(
    session: AsyncSession,
    *,
    profile_access_id: str,
    revoke_reason: str | None = None,
) -> ProfileAccessRecord:
    access = await session.scalar(
        select(ProfileAccess).where(ProfileAccess.id == profile_access_id).with_for_update()
    )
    if access is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile access was not found.",
        )

    if access.status != "REVOKED":
        access.status = "REVOKED"
        access.revoked_at = utc_now()
        access.revoke_reason = revoke_reason
        await session.flush()

    return ProfileAccessRecord.model_validate(access)


async def _acquire_profile_lock(
    session: AsyncSession,
    account_id: str,
    profile_type: ProfileType,
) -> None:
    lock_key = _build_profile_lock_key(account_id, profile_type)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key},
    )


def _build_profile_lock_key(account_id: str, profile_type: ProfileType) -> int:
    digest = hashlib.blake2b(
        f"{account_id}:{profile_type.value}".encode(),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


async def _validate_profile_access_pair(
    session: AsyncSession,
    *,
    accessor_profile_id: str,
    primary_profile_id: str,
) -> tuple[Profile, Profile]:
    accessor_profile = await session.get(Profile, accessor_profile_id)
    if accessor_profile is None or not accessor_profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accessor profile was not found.",
        )
    if accessor_profile.profile_type not in {ProfileType.ADVISOR, ProfileType.NOMINEE}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accessor profile must be an advisor or nominee profile.",
        )

    primary_profile = await session.get(Profile, primary_profile_id)
    if primary_profile is None or not primary_profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Primary profile was not found.",
        )
    if primary_profile.profile_type != ProfileType.PRIMARY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primary profile access targets must use a primary profile.",
        )

    if accessor_profile.id == primary_profile.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile access cannot target the same profile.",
        )

    return accessor_profile, primary_profile


async def _acquire_profile_access_lock(
    session: AsyncSession,
    accessor_profile_id: str,
    primary_profile_id: str,
) -> None:
    digest = hashlib.blake2b(
        f"{accessor_profile_id}:{primary_profile_id}".encode(),
        digest_size=8,
    ).digest()
    lock_key = int.from_bytes(digest, byteorder="big", signed=True)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key},
    )
