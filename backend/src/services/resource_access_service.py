from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Profile, ProfileAccess, ProfileType
from services.auth_service import AuthenticatedAccountContext

NOMINEE_PERMISSION_SUMMARY = "VIEW_SUMMARY"
NOMINEE_PERMISSION_FULL = "VIEW_FULL"
NOMINEE_PERMISSION_WITH_DOCUMENTS = "VIEW_WITH_DOCUMENTS"


@dataclass(frozen=True)
class ResolvedResourceContext:
    actor_profile: Profile
    primary_profile: Profile
    profile_access: ProfileAccess | None
    primary_account_id: str
    can_write: bool

    @property
    def is_nominee(self) -> bool:
        return self.actor_profile.profile_type == ProfileType.NOMINEE

    @property
    def is_advisor(self) -> bool:
        return self.actor_profile.profile_type == ProfileType.ADVISOR

    @property
    def is_primary(self) -> bool:
        return self.actor_profile.profile_type == ProfileType.PRIMARY


async def resolve_resource_context(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    profile_id: str,
    primary_profile_id: str | None,
    require_write: bool,
) -> ResolvedResourceContext:
    actor_profile = await session.scalar(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.account_id == auth_context.account.id,
            Profile.is_active.is_(True),
        )
    )
    if actor_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile was not found.",
        )

    if actor_profile.profile_type == ProfileType.PRIMARY:
        if primary_profile_id is not None and primary_profile_id != actor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Primary profiles may only act on their own workspace.",
            )
        return ResolvedResourceContext(
            actor_profile=actor_profile,
            primary_profile=actor_profile,
            profile_access=None,
            primary_account_id=actor_profile.account_id,
            can_write=True,
        )

    if primary_profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="primary_profile_id is required for advisor and nominee access.",
        )

    primary_profile = await session.scalar(
        select(Profile).where(
            Profile.id == primary_profile_id,
            Profile.profile_type == ProfileType.PRIMARY,
            Profile.is_active.is_(True),
        )
    )
    if primary_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Primary profile was not found.",
        )

    profile_access = await session.scalar(
        select(ProfileAccess).where(
            ProfileAccess.accessor_profile_id == actor_profile.id,
            ProfileAccess.primary_profile_id == primary_profile.id,
            ProfileAccess.status == "ACTIVE",
        )
    )
    if profile_access is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This profile cannot access the requested primary workspace.",
        )

    can_write = actor_profile.profile_type == ProfileType.ADVISOR
    if require_write and not can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This profile cannot modify the requested resource.",
        )

    return ResolvedResourceContext(
        actor_profile=actor_profile,
        primary_profile=primary_profile,
        profile_access=profile_access,
        primary_account_id=primary_profile.account_id,
        can_write=can_write,
    )
