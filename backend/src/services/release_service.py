from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import utc_now
from core.settings import get_settings
from db.models import (
    AccountInactivityState,
    AccountNomineeScope,
)


@dataclass(frozen=True)
class InactivityRunSummary:
    reminders_sent: int
    escalations_sent: int
    verifications_initiated: int
    releases_completed: int


async def run_inactivity_checks(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> InactivityRunSummary:
    run_at = now or utc_now()
    reminders_sent = await send_reminders(session, now=run_at)
    escalations_sent = await send_escalations(session, now=run_at)
    verifications_initiated = await initiate_nominee_verification(session, now=run_at)

    states = (
        await session.scalars(
            select(AccountInactivityState).where(
                AccountInactivityState.current_state == "HOLD",
                AccountInactivityState.hold_expires_at.is_not(None),
                AccountInactivityState.hold_expires_at <= run_at,
            )
        )
    ).all()
    releases_completed = 0
    for state in states:
        await complete_release(session, account_id=state.account_id, now=run_at)
        releases_completed += 1

    return InactivityRunSummary(
        reminders_sent=reminders_sent,
        escalations_sent=escalations_sent,
        verifications_initiated=verifications_initiated,
        releases_completed=releases_completed,
    )


async def send_reminders(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    run_at = now or utc_now()
    threshold = run_at - timedelta(days=get_settings().inactivity_reminder_days)
    states = (
        await session.scalars(
            select(AccountInactivityState)
            .where(
                AccountInactivityState.current_state == "ACTIVE",
                AccountInactivityState.last_active_at.is_not(None),
                AccountInactivityState.last_active_at <= threshold,
                AccountInactivityState.reminder_sent_at.is_(None),
            )
            .with_for_update()
        )
    ).all()

    for state in states:
        state.current_state = "REMINDER_SENT"
        state.reminder_sent_at = run_at
        state.reminder_count += 1

    return len(states)


async def send_escalations(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    run_at = now or utc_now()
    threshold = run_at - timedelta(days=get_settings().inactivity_escalation_days)
    states = (
        await session.scalars(
            select(AccountInactivityState)
            .where(
                AccountInactivityState.current_state.in_(["ACTIVE", "REMINDER_SENT"]),
                AccountInactivityState.last_active_at.is_not(None),
                AccountInactivityState.last_active_at <= threshold,
                AccountInactivityState.escalation_sent_at.is_(None),
            )
            .with_for_update()
        )
    ).all()

    for state in states:
        state.current_state = "ESCALATED"
        state.escalation_sent_at = run_at

    return len(states)


async def initiate_nominee_verification(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    run_at = now or utc_now()
    threshold = run_at - timedelta(days=get_settings().inactivity_trigger_days)
    states = (
        await session.scalars(
            select(AccountInactivityState)
            .where(
                AccountInactivityState.current_state.in_(["ACTIVE", "REMINDER_SENT", "ESCALATED"]),
                AccountInactivityState.last_active_at.is_not(None),
                AccountInactivityState.last_active_at <= threshold,
                AccountInactivityState.trigger_initiated_at.is_(None),
            )
            .with_for_update()
        )
    ).all()

    for state in states:
        state.current_state = "TRIGGERED"
        state.trigger_initiated_at = run_at

    return len(states)


async def start_hold(
    session: AsyncSession,
    *,
    account_id: str,
    now: datetime | None = None,
) -> AccountInactivityState:
    run_at = now or utc_now()
    state = await _get_inactivity_state_for_update(session, account_id)
    if state.current_state == "HOLD":
        return state
    if state.current_state != "TRIGGERED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only triggered accounts can enter the hold window.",
        )

    state.current_state = "HOLD"
    state.hold_started_at = run_at
    state.hold_expires_at = run_at + timedelta(days=get_settings().release_hold_days)
    return state


async def complete_release(
    session: AsyncSession,
    *,
    account_id: str,
    now: datetime | None = None,
    trigger_source: str = "INACTIVITY_TRIGGER",
) -> AccountInactivityState:
    run_at = now or utc_now()
    state = await _get_inactivity_state_for_update(session, account_id)
    if state.current_state == "RELEASED":
        return state
    if state.current_state != "HOLD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only held accounts can be released.",
        )
    if state.hold_expires_at is None or state.hold_expires_at > run_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The hold period has not expired yet.",
        )

    state.current_state = "RELEASED"
    state.released_at = run_at

    nominee_scopes = (
        await session.scalars(
            select(AccountNomineeScope)
            .join(AccountNomineeScope.account_nominee)
            .where(
                AccountNomineeScope.is_active.is_(True),
                AccountNomineeScope.is_visible.is_(False),
                AccountNomineeScope.account_nominee.has(primary_account_id=account_id),
            )
            .with_for_update()
        )
    ).all()
    for scope_row in nominee_scopes:
        scope_row.is_visible = True
        scope_row.visibility_triggered_at = run_at
        scope_row.visibility_trigger_source = trigger_source

    return state


async def _get_inactivity_state_for_update(
    session: AsyncSession,
    account_id: str,
) -> AccountInactivityState:
    state = await session.scalar(
        select(AccountInactivityState)
        .where(AccountInactivityState.account_id == account_id)
        .with_for_update()
    )
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inactivity state was not found.",
        )
    return state
