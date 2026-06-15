from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.dependencies.auth import get_current_account_context
from api.routes import profiles as profile_routes
from app import app
from core.security import create_jwt
from db.models import Profile, ProfileAccess, ProfileType
from services import profile_service
from services.auth_service import AuthenticatedAccountContext

client = TestClient(app)
TEST_SECRET = "test-secret-key-which-is-definitely-long-enough"


def _build_profile_response(profile_type: str = "ADVISOR", created: bool = True) -> dict:
    return {
        "profile": {
            "id": "profile-123",
            "account_id": "account-123",
            "profile_type": profile_type,
            "is_active": True,
            "created_at": "2030-01-01T00:00:00Z",
            "updated_at": "2030-01-01T00:00:00Z",
        },
        "created": created,
    }


def _build_profile_detail(profile_id: str = "profile-123", profile_type: str = "PRIMARY") -> dict:
    return {
        "id": profile_id,
        "account_id": "account-123",
        "profile_type": profile_type,
        "is_active": True,
        "created_at": "2030-01-01T00:00:00Z",
        "updated_at": "2030-01-01T00:00:00Z",
    }


def _build_auth_context() -> AuthenticatedAccountContext:
    _, claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-primary"},
    )
    return AuthenticatedAccountContext(
        account=SimpleNamespace(
            id="account-123",
            email="user@example.com",
            phone="919999999999",
            full_name="Test User",
            email_verified=False,
            phone_verified=True,
            status="ACTIVE",
        ),
        profile_id="profile-primary",
        claims=claims,
        session_id="session-123",
    )


def test_profile_types_catalog() -> None:
    response = client.get("/api/v1/profiles/types")

    assert response.status_code == 200
    assert response.json()["supported_types"] == ["PRIMARY", "ADVISOR", "NOMINEE"]


def test_list_profiles_requires_authentication() -> None:
    response = client.get("/api/v1/profiles")

    assert response.status_code == 401


def test_list_profiles_returns_owned_profiles(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_list_profiles(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        assert auth_context.account.id == "account-123"
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return {
            "items": [
                _build_profile_detail(profile_id="profile-primary", profile_type="PRIMARY"),
                _build_profile_detail(profile_id="profile-advisor", profile_type="ADVISOR"),
            ],
            "total": 2,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }

    monkeypatch.setattr(profile_routes, "list_profiles", fake_list_profiles)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get(
            "/api/v1/profiles",
            headers={"Authorization": "Bearer access-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [item["profile_type"] for item in response.json()["items"]] == [
        "PRIMARY",
        "ADVISOR",
    ]


def test_create_profile_requires_authentication() -> None:
    response = client.post("/api/v1/profiles", json={"profile_type": "ADVISOR"})

    assert response.status_code == 401


def test_create_profile_rejects_non_advisor_type() -> None:
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/profiles",
            headers={"Authorization": "Bearer access-token"},
            json={"profile_type": "NOMINEE"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Only advisor profiles can be created through this endpoint."
    )


def test_create_profile_returns_upserted_advisor(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_create_advisor_profile(session, auth_context):  # type: ignore[no-untyped-def]
        assert auth_context.account.id == "account-123"
        return _build_profile_response()

    monkeypatch.setattr(profile_routes, "create_advisor_profile", fake_create_advisor_profile)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/profiles",
            headers={"Authorization": "Bearer access-token"},
            json={"profile_type": "advisor"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["profile"]["profile_type"] == "ADVISOR"
    assert response.json()["created"] is True


def test_get_profile_returns_owned_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_get_profile(session, auth_context, profile_id):  # type: ignore[no-untyped-def]
        assert profile_id == "profile-primary"
        assert auth_context.account.id == "account-123"
        return _build_profile_detail(profile_id="profile-primary", profile_type="PRIMARY")

    monkeypatch.setattr(profile_routes, "get_profile", fake_get_profile)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get(
            "/api/v1/profiles/profile-primary",
            headers={"Authorization": "Bearer access-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "profile-primary"
    assert response.json()["profile_type"] == "PRIMARY"


class _FakeProfileSession:
    def __init__(self, existing_profile: Profile | None = None):
        self.existing_profile = existing_profile
        self.lock_calls = 0
        self.added = []
        self.flushed = False

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        if "pg_advisory_xact_lock" not in str(statement):
            raise AssertionError("Expected advisory lock before profile creation.")
        assert params and "lock_key" in params
        self.lock_calls += 1
        return None

    async def scalar(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return self.existing_profile

    def add(self, item):  # type: ignore[no-untyped-def]
        self.added.append(item)

    async def flush(self) -> None:
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = str(uuid4())
        self.flushed = True

    async def refresh(self, _item) -> None:  # type: ignore[no-untyped-def]
        return None


class _FakeProfileAccessSession(_FakeProfileSession):
    def __init__(
        self,
        *,
        profiles_by_id: dict[str, Profile] | None = None,
        existing_access: ProfileAccess | None = None,
    ):
        super().__init__()
        self.profiles_by_id = profiles_by_id or {}
        self.existing_access = existing_access

    async def scalar(self, statement, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        statement_text = str(statement)
        if "FROM profile_access" in statement_text:
            return self.existing_access
        return self.existing_profile

    async def get(self, model, primary_key, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        if model is Profile:
            return self.profiles_by_id.get(primary_key)
        return None


@pytest.mark.asyncio
async def test_ensure_profile_returns_existing_profile() -> None:
    existing_profile = Profile(
        id="profile-existing",
        account_id="account-123",
        profile_type=ProfileType.ADVISOR,
        is_active=True,
    )
    fake_session = _FakeProfileSession(existing_profile)

    profile, created = await profile_service.ensure_profile(
        fake_session,  # type: ignore[arg-type]
        "account-123",
        ProfileType.ADVISOR,
    )

    assert profile is existing_profile
    assert created is False
    assert fake_session.lock_calls == 1


@pytest.mark.asyncio
async def test_ensure_profile_creates_missing_profile() -> None:
    fake_session = _FakeProfileSession()

    profile, created = await profile_service.ensure_profile(
        fake_session,  # type: ignore[arg-type]
        "account-123",
        ProfileType.NOMINEE,
    )

    assert profile.account_id == "account-123"
    assert profile.profile_type == ProfileType.NOMINEE
    assert profile.is_active is True
    assert created is True
    assert fake_session.flushed is True
    assert fake_session.lock_calls == 1


@pytest.mark.asyncio
async def test_create_profile_access_creates_new_relationship() -> None:
    accessor = Profile(
        id="profile-advisor",
        account_id="account-456",
        profile_type=ProfileType.ADVISOR,
        is_active=True,
    )
    primary = Profile(
        id="profile-primary",
        account_id="account-123",
        profile_type=ProfileType.PRIMARY,
        is_active=True,
    )
    fake_session = _FakeProfileAccessSession(
        profiles_by_id={accessor.id: accessor, primary.id: primary},
    )

    result = await profile_service.create_profile_access(
        fake_session,  # type: ignore[arg-type]
        accessor_profile_id=accessor.id,
        primary_profile_id=primary.id,
    )

    assert result.created is True
    assert result.access.accessor_profile_id == "profile-advisor"
    assert result.access.primary_profile_id == "profile-primary"
    assert result.access.status == "ACTIVE"
    assert fake_session.lock_calls == 1


@pytest.mark.asyncio
async def test_create_profile_access_reactivates_revoked_relationship() -> None:
    now = datetime.now(timezone.utc)
    accessor = Profile(
        id="profile-nominee",
        account_id="account-789",
        profile_type=ProfileType.NOMINEE,
        is_active=True,
    )
    primary = Profile(
        id="profile-primary",
        account_id="account-123",
        profile_type=ProfileType.PRIMARY,
        is_active=True,
    )
    existing_access = ProfileAccess(
        id="access-123",
        accessor_profile_id=accessor.id,
        primary_profile_id=primary.id,
        status="REVOKED",
        granted_at=now,
        revoked_at=now,
        revoke_reason="old",
    )
    fake_session = _FakeProfileAccessSession(
        profiles_by_id={accessor.id: accessor, primary.id: primary},
        existing_access=existing_access,
    )

    result = await profile_service.create_profile_access(
        fake_session,  # type: ignore[arg-type]
        accessor_profile_id=accessor.id,
        primary_profile_id=primary.id,
    )

    assert result.created is False
    assert result.access.status == "ACTIVE"
    assert existing_access.revoke_reason is None
    assert existing_access.revoked_at is None


@pytest.mark.asyncio
async def test_revoke_profile_access_marks_record_revoked() -> None:
    now = datetime.now(timezone.utc)
    access = ProfileAccess(
        id="access-123",
        accessor_profile_id="profile-advisor",
        primary_profile_id="profile-primary",
        status="ACTIVE",
        granted_at=now,
        revoked_at=None,
        revoke_reason=None,
    )
    fake_session = _FakeProfileAccessSession(existing_access=access)

    result = await profile_service.revoke_profile_access(
        fake_session,  # type: ignore[arg-type]
        profile_access_id="access-123",
        revoke_reason="Manual revoke",
    )

    assert result.status == "REVOKED"
    assert result.revoke_reason == "Manual revoke"
