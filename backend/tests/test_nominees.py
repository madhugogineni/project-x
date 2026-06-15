from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.dependencies.auth import get_current_account_context
from api.routes import nominees as nominees_routes
from app import app
from core.security import create_jwt
from services import nominee_service
from services.auth_service import AuthenticatedAccountContext

client = TestClient(app)
TEST_SECRET = "test-secret-key-which-is-definitely-long-enough"


def _build_nominee_response() -> dict:
    now = datetime(2030, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "id": "nominee-123",
        "full_name": "Jane Doe",
        "relationship": "SPOUSE",
        "phone": "919999999998",
        "email": "jane@example.com",
        "share_percentage": 50.0,
        "status": "PENDING",
        "linked_account_id": None,
        "linked_at": None,
        "linked_account": None,
        "created_at": now,
        "updated_at": now,
    }


def _build_scope_response() -> dict:
    now = datetime(2030, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "id": "scope-123",
        "container_id": "container-123",
        "container_type": "BANK_RELATIONSHIP",
        "institution_name": "Acme Bank",
        "permission": "VIEW_FULL",
        "is_active": True,
        "is_visible": False,
        "visibility_triggered_at": None,
        "visibility_trigger_source": None,
        "created_at": now,
        "updated_at": now,
    }


def _override_auth_context() -> AuthenticatedAccountContext:
    _, claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123"},
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
        profile_id="profile-123",
        claims=claims,
        session_id="session-123",
    )


def test_nominee_list_requires_authentication() -> None:
    response = client.get("/api/v1/nominees")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


def test_nominee_list_returns_records(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_list_nominees(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        assert auth_context.account.id == "account-123"
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return {
            "items": [_build_nominee_response()],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }

    monkeypatch.setattr(nominees_routes, "list_nominees", fake_list_nominees)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get("/api/v1/nominees", headers={"Authorization": "Bearer access-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["full_name"] == "Jane Doe"


def test_nominee_create_requires_phone_and_email() -> None:
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/nominees",
            headers={"Authorization": "Bearer access-token"},
            json={
                "full_name": "Jane Doe",
                "relationship": "spouse",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "Field required" in response.text


def test_nominee_create_returns_created_record(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_create_nominee(session, auth_context, payload):  # type: ignore[no-untyped-def]
        assert payload.full_name == "Jane Doe"
        assert payload.relationship == "SPOUSE"
        assert payload.phone == "919999999998"
        assert payload.email == "jane@example.com"
        return _build_nominee_response()

    monkeypatch.setattr(nominees_routes, "create_nominee", fake_create_nominee)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/nominees",
            headers={"Authorization": "Bearer access-token"},
            json={
                "full_name": "Jane Doe",
                "relationship": "spouse",
                "phone": "+91 99999 99998",
                "email": "jane@example.com",
                "share_percentage": 50,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["relationship"] == "SPOUSE"


def test_nominee_create_accepts_custom_relationship(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_create_nominee(session, auth_context, payload):  # type: ignore[no-untyped-def]
        assert payload.relationship == "MOTHER-IN-LAW"
        response = _build_nominee_response()
        response["relationship"] = payload.relationship
        return response

    monkeypatch.setattr(nominees_routes, "create_nominee", fake_create_nominee)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/nominees",
            headers={"Authorization": "Bearer access-token"},
            json={
                "full_name": "Jane Doe",
                "relationship": "Mother-in-law",
                "phone": "+91 99999 99998",
                "email": "jane@example.com",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["relationship"] == "MOTHER-IN-LAW"


def test_nominee_create_rejects_missing_email() -> None:
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/nominees",
            headers={"Authorization": "Bearer access-token"},
            json={
                "full_name": "Jane Doe",
                "relationship": "spouse",
                "phone": "+91 99999 99998",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "Field required" in response.text


def test_nominee_contact_rejects_primary_phone() -> None:
    auth_context = _override_auth_context()

    with pytest.raises(HTTPException) as exc_info:
        nominee_service._validate_nominee_contact(
            nominee_phone="+91 99999 99999",
            nominee_email="nominee@example.com",
            auth_context=auth_context,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Nominee phone number cannot match your phone number."


def test_nominee_contact_rejects_primary_email() -> None:
    auth_context = _override_auth_context()

    with pytest.raises(HTTPException) as exc_info:
        nominee_service._validate_nominee_contact(
            nominee_phone="+91 99999 99998",
            nominee_email="USER@example.com",
            auth_context=auth_context,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Nominee email cannot match your email."


def test_nominee_update_requires_fields(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.patch(
            "/api/v1/nominees/nominee-123",
            headers={"Authorization": "Bearer access-token"},
            json={},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "At least one nominee field must be provided." in response.text


def test_nominee_update_returns_record(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_update_nominee(session, auth_context, nominee_id, payload):  # type: ignore[no-untyped-def]
        assert nominee_id == "nominee-123"
        assert payload.relationship == "PARENT"
        response = _build_nominee_response()
        response["relationship"] = "PARENT"
        return response

    monkeypatch.setattr(nominees_routes, "update_nominee", fake_update_nominee)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.patch(
            "/api/v1/nominees/nominee-123",
            headers={"Authorization": "Bearer access-token"},
            json={"relationship": "parent"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["relationship"] == "PARENT"


def test_nominee_delete_returns_removed_record(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_remove_nominee(session, auth_context, nominee_id):  # type: ignore[no-untyped-def]
        assert nominee_id == "nominee-123"
        response = _build_nominee_response()
        response["status"] = "REMOVED"
        return response

    monkeypatch.setattr(nominees_routes, "remove_nominee", fake_remove_nominee)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.delete(
            "/api/v1/nominees/nominee-123",
            headers={"Authorization": "Bearer access-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "REMOVED"


def test_nominee_scope_list_returns_rows(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_get_nominee_scope(session, auth_context, nominee_id, **kwargs):  # type: ignore[no-untyped-def]
        assert nominee_id == "nominee-123"
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return {
            "items": [_build_scope_response()],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }

    monkeypatch.setattr(nominees_routes, "get_nominee_scope", fake_get_nominee_scope)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get(
            "/api/v1/nominees/nominee-123/scope",
            headers={"Authorization": "Bearer access-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["institution_name"] == "Acme Bank"


def test_nominee_scope_replace_rejects_duplicate_containers(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.put(
            "/api/v1/nominees/nominee-123/scope",
            headers={"Authorization": "Bearer access-token"},
            json={
                "scopes": [
                    {"container_id": "container-123", "permission": "view_full"},
                    {"container_id": "container-123", "permission": "view_summary"},
                ]
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "Each container may only appear once in scope." in response.text


def test_nominee_scope_replace_returns_rows(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_replace_nominee_scope(session, auth_context, nominee_id, payload):  # type: ignore[no-untyped-def]
        assert nominee_id == "nominee-123"
        assert payload.scopes[0].permission == "VIEW_WITH_DOCUMENTS"
        return [_build_scope_response()]

    monkeypatch.setattr(nominees_routes, "replace_nominee_scope", fake_replace_nominee_scope)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.put(
            "/api/v1/nominees/nominee-123/scope",
            headers={"Authorization": "Bearer access-token"},
            json={
                "scopes": [
                    {
                        "container_id": "container-123",
                        "permission": "view_with_documents",
                    }
                ]
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["permission"] == "VIEW_FULL"


def test_nominee_visibility_requires_selection_mode(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.put(
            "/api/v1/nominees/nominee-123/visibility",
            headers={"Authorization": "Bearer access-token"},
            json={"is_visible": True, "all_assigned": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "Specify either all_assigned=true or a non-empty container_ids list." in response.text


def test_nominee_visibility_update_returns_rows(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _override_auth_context()

    async def fake_update_nominee_visibility(session, auth_context, nominee_id, payload):  # type: ignore[no-untyped-def]
        assert nominee_id == "nominee-123"
        assert payload.is_visible is True
        assert payload.container_ids == ["container-123"]
        return [_build_scope_response()]

    monkeypatch.setattr(
        nominees_routes,
        "update_nominee_visibility",
        fake_update_nominee_visibility,
    )
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.put(
            "/api/v1/nominees/nominee-123/visibility",
            headers={"Authorization": "Bearer access-token"},
            json={
                "is_visible": True,
                "container_ids": ["container-123"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["container_id"] == "container-123"


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _FakeNomineeLinkSession:
    def __init__(self, nominees):
        self.nominees = nominees
        self.flushed = False

    async def scalars(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return _FakeScalarsResult(self.nominees)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_autolink_nominee_records_links_first_match_per_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nominee_a = SimpleNamespace(
        id="nominee-a",
        primary_account_id="primary-1",
        email="user@example.com",
        linked_account_id=None,
        nominee_profile_id=None,
        linked_at=None,
        status="PENDING",
    )
    nominee_b = SimpleNamespace(
        id="nominee-b",
        primary_account_id="primary-1",
        email="user@example.com",
        linked_account_id=None,
        nominee_profile_id=None,
        linked_at=None,
        status="PENDING",
    )
    nominee_c = SimpleNamespace(
        id="nominee-c",
        primary_account_id="primary-2",
        email=None,
        linked_account_id=None,
        nominee_profile_id=None,
        linked_at=None,
        status="INVITED",
    )
    fake_session = _FakeNomineeLinkSession([nominee_a, nominee_b, nominee_c])

    ensured_primary_profiles = []
    created_access_pairs = []

    async def fake_ensure_profile(session, account_id, profile_type):  # type: ignore[no-untyped-def]
        ensured_primary_profiles.append((account_id, profile_type))
        return SimpleNamespace(id=f"profile-{account_id}"), True

    async def fake_create_profile_access(
        session,
        *,
        accessor_profile_id,
        primary_profile_id,
    ):  # type: ignore[no-untyped-def]
        created_access_pairs.append((accessor_profile_id, primary_profile_id))
        return None

    monkeypatch.setattr(nominee_service, "ensure_profile", fake_ensure_profile)
    monkeypatch.setattr(nominee_service, "create_profile_access", fake_create_profile_access)

    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    await nominee_service.autolink_nominee_records_for_account(
        fake_session,  # type: ignore[arg-type]
        account=SimpleNamespace(
            id="account-123",
            phone="919999999999",
            email="user@example.com",
        ),
        nominee_profile_id="nominee-profile-123",
        now=now,
    )

    assert nominee_a.linked_account_id == "account-123"
    assert nominee_a.nominee_profile_id == "nominee-profile-123"
    assert nominee_a.linked_at == now
    assert nominee_a.status == "LINKED"

    assert nominee_b.linked_account_id is None
    assert nominee_b.nominee_profile_id is None

    assert nominee_c.linked_account_id == "account-123"
    assert nominee_c.nominee_profile_id == "nominee-profile-123"
    assert nominee_c.status == "LINKED"

    assert ensured_primary_profiles == [
        ("primary-1", nominee_service.ProfileType.PRIMARY),
        ("primary-2", nominee_service.ProfileType.PRIMARY),
    ]
    assert created_access_pairs == [
        ("nominee-profile-123", "profile-primary-1"),
        ("nominee-profile-123", "profile-primary-2"),
    ]
    assert fake_session.flushed is True
