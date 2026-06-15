from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.security import utc_now
from db.models import (
    Account,
    AccountNominee,
    AccountNomineeScope,
    Asset,
    Profile,
    ProfileType,
)
from schemas.nominee import (
    EDITABLE_NOMINEE_STATUSES,
    LinkedAccountResponse,
    NomineeCreateRequest,
    NomineeResponse,
    NomineeScopeReplaceRequest,
    NomineeScopeResponse,
    NomineeUpdateRequest,
    NomineeVisibilityUpdateRequest,
)
from schemas.pagination import PaginatedResponse, build_paginated_response
from services.profile_service import create_profile_access, ensure_profile

if TYPE_CHECKING:
    from services.auth_service import AuthenticatedAccountContext


async def list_nominees(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    limit: int,
    offset: int,
) -> PaginatedResponse[NomineeResponse]:
    primary_account_id = await _require_primary_profile_context(session, auth_context)
    total = await session.scalar(
        select(func.count())
        .select_from(AccountNominee)
        .where(
            AccountNominee.primary_account_id == primary_account_id,
            AccountNominee.status != "REMOVED",
        )
    )
    nominees = (
        await session.scalars(
            select(AccountNominee)
            .options(selectinload(AccountNominee.linked_account))
            .where(
                AccountNominee.primary_account_id == primary_account_id,
                AccountNominee.status != "REMOVED",
            )
            .order_by(AccountNominee.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return build_paginated_response(
        items=[_build_nominee_response(nominee) for nominee in nominees],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


async def create_nominee(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    payload: NomineeCreateRequest,
) -> NomineeResponse:
    primary_account_id = await _require_primary_profile_context(session, auth_context)
    _validate_nominee_contact(
        nominee_phone=payload.phone,
        nominee_email=payload.email,
        auth_context=auth_context,
    )
    nominee = AccountNominee(
        primary_account_id=primary_account_id,
        added_by_account_id=auth_context.account.id,
        full_name=payload.full_name,
        nominee_relationship=payload.relationship,
        phone=payload.phone,
        email=payload.email,
        share_percentage=payload.share_percentage,
        status="PENDING",
    )
    session.add(nominee)
    await session.flush()
    await session.refresh(nominee)
    return _build_nominee_response(nominee)


async def get_nominee(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    nominee_id: str,
) -> NomineeResponse:
    nominee = await _get_nominee_for_primary(
        session,
        auth_context,
        nominee_id,
        for_update=False,
    )
    return _build_nominee_response(nominee)


async def update_nominee(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    nominee_id: str,
    payload: NomineeUpdateRequest,
) -> NomineeResponse:
    nominee = await _get_nominee_for_primary(
        session,
        auth_context,
        nominee_id,
        for_update=True,
    )
    if nominee.status not in EDITABLE_NOMINEE_STATUSES:
        raise _bad_request_error(
            "Only pending or invited nominees can be updated.",
        )

    next_phone = payload.phone if payload.phone is not None else nominee.phone
    next_email = payload.email if payload.email is not None else nominee.email
    _validate_nominee_contact(
        nominee_phone=next_phone,
        nominee_email=next_email,
        auth_context=auth_context,
    )

    if payload.full_name is not None:
        nominee.full_name = payload.full_name
    if payload.relationship is not None:
        nominee.nominee_relationship = payload.relationship
    if payload.phone is not None:
        nominee.phone = payload.phone
    if payload.email is not None:
        nominee.email = payload.email
    if payload.share_percentage is not None:
        nominee.share_percentage = payload.share_percentage

    await session.flush()
    await session.refresh(nominee)
    return _build_nominee_response(nominee)


async def remove_nominee(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    nominee_id: str,
) -> NomineeResponse:
    nominee = await _get_nominee_for_primary(
        session,
        auth_context,
        nominee_id,
        for_update=True,
    )
    if nominee.status != "REMOVED":
        nominee.status = "REMOVED"
        scope_rows = (
            await session.scalars(
                select(AccountNomineeScope).where(
                    AccountNomineeScope.account_nominee_id == nominee.id,
                    AccountNomineeScope.is_active.is_(True),
                )
            )
        ).all()
        for row in scope_rows:
            row.is_active = False
        await session.flush()
        await session.refresh(nominee)

    return _build_nominee_response(nominee)


async def get_nominee_scope(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    nominee_id: str,
    *,
    limit: int,
    offset: int,
) -> PaginatedResponse[NomineeScopeResponse]:
    nominee = await _get_nominee_for_primary(
        session,
        auth_context,
        nominee_id,
        for_update=False,
    )
    return await _build_scope_response_rows(
        session,
        nominee.id,
        limit=limit,
        offset=offset,
    )


async def replace_nominee_scope(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    nominee_id: str,
    payload: NomineeScopeReplaceRequest,
) -> list[NomineeScopeResponse]:
    nominee = await _get_nominee_for_primary(
        session,
        auth_context,
        nominee_id,
        for_update=True,
    )
    if nominee.status == "REMOVED":
        raise _bad_request_error("Removed nominees cannot be assigned scope.")

    primary_account_id = await _require_primary_profile_context(session, auth_context)
    container_ids = [scope.container_id for scope in payload.scopes]
    containers_by_id = await _get_primary_asset_containers(
        session,
        primary_account_id=primary_account_id,
        container_ids=container_ids,
    )

    if len(containers_by_id) != len(set(container_ids)):
        missing_ids = sorted(set(container_ids) - set(containers_by_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset containers not found for nominee scope: {', '.join(missing_ids)}",
        )

    existing_rows = (
        await session.scalars(
            select(AccountNomineeScope)
            .where(AccountNomineeScope.account_nominee_id == nominee.id)
            .with_for_update()
        )
    ).all()
    existing_by_container = {row.container_id: row for row in existing_rows}
    active_container_ids = set()

    for scope in payload.scopes:
        active_container_ids.add(scope.container_id)
        row = existing_by_container.get(scope.container_id)
        if row is None:
            row = AccountNomineeScope(
                account_nominee_id=nominee.id,
                added_by_account_id=auth_context.account.id,
                container_id=scope.container_id,
                permission=scope.permission,
                is_active=True,
                is_visible=False,
            )
            session.add(row)
            existing_by_container[scope.container_id] = row
            continue

        row.permission = scope.permission
        row.added_by_account_id = auth_context.account.id
        row.is_active = True

    for row in existing_rows:
        if row.container_id not in active_container_ids:
            row.is_active = False

    await session.flush()
    return (
        await _build_scope_response_rows(
            session,
            nominee.id,
            limit=1000,
            offset=0,
        )
    ).items


async def update_nominee_visibility(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    nominee_id: str,
    payload: NomineeVisibilityUpdateRequest,
) -> list[NomineeScopeResponse]:
    nominee = await _get_nominee_for_primary(
        session,
        auth_context,
        nominee_id,
        for_update=True,
    )
    if nominee.status == "REMOVED":
        raise _bad_request_error("Removed nominees cannot be assigned visibility.")

    scope_rows = (
        await session.scalars(
            select(AccountNomineeScope)
            .where(
                AccountNomineeScope.account_nominee_id == nominee.id,
                AccountNomineeScope.is_active.is_(True),
            )
            .with_for_update()
        )
    ).all()
    if payload.all_assigned:
        target_rows = scope_rows
    else:
        requested_ids = set(payload.container_ids or [])
        rows_by_container = {row.container_id: row for row in scope_rows}
        missing_ids = sorted(requested_ids - set(rows_by_container))
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Assigned nominee scope rows were not found for: " + ", ".join(missing_ids)
                ),
            )
        target_rows = [rows_by_container[container_id] for container_id in requested_ids]

    visibility_source = "PRIMARY_GRANTED" if payload.is_visible else "PRIMARY_REVOKED"
    changed_at = utc_now()
    for row in target_rows:
        row.is_visible = payload.is_visible
        row.visibility_triggered_at = changed_at
        row.visibility_trigger_source = visibility_source

    await session.flush()
    return (
        await _build_scope_response_rows(
            session,
            nominee.id,
            limit=1000,
            offset=0,
        )
    ).items


async def autolink_nominee_records_for_account(
    session: AsyncSession,
    *,
    account: Account,
    nominee_profile_id: str,
    now: datetime | None = None,
) -> None:
    linked_at = now or utc_now()
    candidates = (
        await session.scalars(
            select(AccountNominee)
            .where(
                AccountNominee.linked_account_id.is_(None),
                AccountNominee.nominee_profile_id.is_(None),
                AccountNominee.phone == account.phone,
                AccountNominee.status != "REMOVED",
            )
            .order_by(AccountNominee.primary_account_id.asc(), AccountNominee.created_at.asc())
            .with_for_update()
        )
    ).all()

    linked_primary_account_ids: set[str] = set()
    for nominee in candidates:
        if nominee.primary_account_id in linked_primary_account_ids:
            continue
        if nominee.email is not None and nominee.email != account.email:
            continue

        nominee.linked_account_id = account.id
        nominee.nominee_profile_id = nominee_profile_id
        nominee.linked_at = linked_at
        nominee.status = "LINKED"

        primary_profile, _created = await ensure_profile(
            session,
            nominee.primary_account_id,
            ProfileType.PRIMARY,
        )
        await create_profile_access(
            session,
            accessor_profile_id=nominee_profile_id,
            primary_profile_id=primary_profile.id,
        )
        linked_primary_account_ids.add(nominee.primary_account_id)

    await session.flush()


async def _get_nominee_for_primary(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    nominee_id: str,
    *,
    for_update: bool,
) -> AccountNominee:
    primary_account_id = await _require_primary_profile_context(session, auth_context)
    statement = (
        select(AccountNominee)
        .options(selectinload(AccountNominee.linked_account))
        .where(
            AccountNominee.id == nominee_id,
            AccountNominee.primary_account_id == primary_account_id,
        )
    )
    if for_update:
        statement = statement.with_for_update()

    nominee = await session.scalar(statement)
    if nominee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nominee not found.",
        )
    return nominee


async def _build_scope_response_rows(
    session: AsyncSession,
    nominee_id: str,
    *,
    limit: int,
    offset: int,
) -> PaginatedResponse[NomineeScopeResponse]:
    total = await session.scalar(
        select(func.count())
        .select_from(AccountNomineeScope)
        .where(
            AccountNomineeScope.account_nominee_id == nominee_id,
            AccountNomineeScope.is_active.is_(True),
        )
    )
    rows = (
        await session.scalars(
            select(AccountNomineeScope)
            .where(
                AccountNomineeScope.account_nominee_id == nominee_id,
                AccountNomineeScope.is_active.is_(True),
            )
            .order_by(AccountNomineeScope.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    containers_by_id = await _get_primary_asset_containers(
        session,
        primary_account_id=None,
        container_ids=[row.container_id for row in rows],
    )

    responses: list[NomineeScopeResponse] = []
    for row in rows:
        container = containers_by_id.get(row.container_id)
        if container is None:
            continue
        responses.append(
            NomineeScopeResponse(
                id=row.id,
                container_id=row.container_id,
                container_type=container.container_type,
                institution_name=container.institution_name,
                permission=row.permission,
                is_active=row.is_active,
                is_visible=row.is_visible,
                visibility_triggered_at=row.visibility_triggered_at,
                visibility_trigger_source=row.visibility_trigger_source,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return build_paginated_response(
        items=responses,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


async def _get_primary_asset_containers(
    session: AsyncSession,
    *,
    primary_account_id: str | None,
    container_ids: list[str],
) -> dict[str, Asset]:
    if not container_ids:
        return {}

    statement = select(Asset).where(Asset.id.in_(set(container_ids)))
    if primary_account_id is not None:
        statement = statement.where(
            Asset.account_id == primary_account_id,
            Asset.is_active.is_(True),
        )

    containers = (await session.scalars(statement)).all()
    return {container.id: container for container in containers}


async def _require_primary_profile_context(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
) -> str:
    profile: Profile | None = None
    if auth_context.profile_id is not None:
        profile = await session.get(Profile, auth_context.profile_id)

    if profile is None:
        profile = await session.scalar(
            select(Profile).where(
                Profile.account_id == auth_context.account.id,
                Profile.profile_type == ProfileType.PRIMARY,
                Profile.is_active.is_(True),
            )
        )

    if (
        profile is None
        or profile.account_id != auth_context.account.id
        or profile.profile_type != ProfileType.PRIMARY
        or not profile.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nominee management requires a primary profile context.",
        )

    return auth_context.account.id


def _same_phone(left: str, right: str) -> bool:
    left_digits = "".join(char for char in left if char.isdigit())
    right_digits = "".join(char for char in right if char.isdigit())
    return bool(left_digits and right_digits and left_digits[-10:] == right_digits[-10:])


def _validate_nominee_contact(
    *,
    nominee_phone: str | None,
    nominee_email: str | None,
    auth_context: AuthenticatedAccountContext,
) -> None:
    if not nominee_phone or not nominee_email:
        raise _bad_request_error("Phone number and email are required.")

    primary_phone = auth_context.account.phone
    primary_email = auth_context.account.email
    if primary_phone and _same_phone(nominee_phone, primary_phone):
        raise _bad_request_error("Nominee phone number cannot match your phone number.")
    if primary_email and nominee_email.strip().lower() == primary_email.strip().lower():
        raise _bad_request_error("Nominee email cannot match your email.")


def _build_nominee_response(nominee: AccountNominee) -> NomineeResponse:
    linked_account = nominee.linked_account
    linked_account_response = None
    if isinstance(linked_account, Account):
        linked_account_response = LinkedAccountResponse(
            id=linked_account.id,
            full_name=linked_account.full_name,
            phone=linked_account.phone,
            email=linked_account.email,
        )

    return NomineeResponse(
        id=nominee.id,
        full_name=nominee.full_name,
        relationship=nominee.nominee_relationship,
        phone=nominee.phone,
        email=nominee.email,
        share_percentage=float(nominee.share_percentage)
        if nominee.share_percentage is not None
        else None,
        status=nominee.status,
        linked_account_id=nominee.linked_account_id,
        linked_at=nominee.linked_at,
        linked_account=linked_account_response,
        created_at=nominee.created_at,
        updated_at=nominee.updated_at,
    )


def _bad_request_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )
