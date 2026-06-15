from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from services import release_service


class _FakeScalarsResult:
    def __init__(self, rows):  # type: ignore[no-untyped-def]
        self._rows = rows

    def all(self):  # type: ignore[no-untyped-def]
        return list(self._rows)


class _FakeReleaseSession:
    def __init__(self, *, scalars_results=None, scalar_result=None):  # type: ignore[no-untyped-def]
        self.scalars_results = list(scalars_results or [])
        self.scalar_result = scalar_result

    async def scalars(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return _FakeScalarsResult(self.scalars_results.pop(0))

    async def scalar(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return self.scalar_result


@pytest.mark.asyncio
async def test_run_inactivity_checks_orchestrates_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_send_reminders(session, *, now):  # type: ignore[no-untyped-def]
        assert now.tzinfo is not None
        return 2

    async def fake_send_escalations(session, *, now):  # type: ignore[no-untyped-def]
        return 1

    async def fake_initiate_verification(session, *, now):  # type: ignore[no-untyped-def]
        return 3

    completed = []

    async def fake_complete_release(session, *, account_id, now):  # type: ignore[no-untyped-def]
        completed.append(account_id)
        return None

    hold_state = SimpleNamespace(account_id="account-1")
    fake_session = _FakeReleaseSession(scalars_results=[[hold_state]])
    run_at = datetime.now(timezone.utc)

    monkeypatch.setattr(release_service, "send_reminders", fake_send_reminders)
    monkeypatch.setattr(release_service, "send_escalations", fake_send_escalations)
    monkeypatch.setattr(
        release_service,
        "initiate_nominee_verification",
        fake_initiate_verification,
    )
    monkeypatch.setattr(release_service, "complete_release", fake_complete_release)

    result = await release_service.run_inactivity_checks(fake_session, now=run_at)  # type: ignore[arg-type]

    assert result.reminders_sent == 2
    assert result.escalations_sent == 1
    assert result.verifications_initiated == 3
    assert result.releases_completed == 1
    assert completed == ["account-1"]


@pytest.mark.asyncio
async def test_start_hold_sets_hold_window(monkeypatch: pytest.MonkeyPatch) -> None:
    run_at = datetime.now(timezone.utc)
    state = SimpleNamespace(
        account_id="account-1",
        current_state="TRIGGERED",
        hold_started_at=None,
        hold_expires_at=None,
    )

    async def fake_get_state(session, account_id):  # type: ignore[no-untyped-def]
        assert account_id == "account-1"
        return state

    monkeypatch.setattr(release_service, "_get_inactivity_state_for_update", fake_get_state)

    result = await release_service.start_hold(
        _FakeReleaseSession(),  # type: ignore[arg-type]
        account_id="account-1",
        now=run_at,
    )

    assert result.current_state == "HOLD"
    assert result.hold_started_at == run_at
    assert result.hold_expires_at == run_at + timedelta(days=7)


@pytest.mark.asyncio
async def test_complete_release_flips_visibility_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    run_at = datetime.now(timezone.utc)
    state = SimpleNamespace(
        account_id="account-1",
        current_state="HOLD",
        hold_expires_at=run_at - timedelta(days=1),
        released_at=None,
    )
    nominee_scope = SimpleNamespace(
        is_visible=False,
        visibility_triggered_at=None,
        visibility_trigger_source=None,
    )

    async def fake_get_state(session, account_id):  # type: ignore[no-untyped-def]
        return state

    monkeypatch.setattr(release_service, "_get_inactivity_state_for_update", fake_get_state)

    fake_session = _FakeReleaseSession(scalars_results=[[nominee_scope]])
    result = await release_service.complete_release(
        fake_session,  # type: ignore[arg-type]
        account_id="account-1",
        now=run_at,
    )

    assert result.current_state == "RELEASED"
    assert result.released_at == run_at
    assert nominee_scope.is_visible is True
