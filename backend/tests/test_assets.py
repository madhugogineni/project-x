from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.dependencies.auth import get_current_account_context
from api.routes import assets as asset_routes
from app import app
from core.security import create_jwt
from services.auth_service import AuthenticatedAccountContext

client = TestClient(app)
TEST_SECRET = "test-secret-key-which-is-definitely-long-enough"


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


def _build_asset_response() -> dict:
    return {
        "id": "asset-123",
        "container_type": "BANK_RELATIONSHIP",
        "institution_name": "Acme Bank",
        "approximate_value": "1000.00",
        "notes": "Primary checking account",
        "is_active": True,
        "detail_summary": {"account_type": "SAVINGS", "account_number": "XXXX4321"},
        "document_count": 1,
        "can_edit": True,
        "can_delete": True,
        "access_permission": None,
        "created_at": "2030-01-01T00:00:00Z",
        "updated_at": "2030-01-01T00:00:00Z",
        "detail": {
            "account_type": "SAVINGS",
            "account_number": "XXXX4321",
            "ifsc_code": "HDFC0001234",
        },
        "documents": [
            {
                "id": "doc-123",
                "container_id": "asset-123",
                "document_type": "ACCOUNT_STATEMENT",
                "original_file_name": "statement.pdf",
                "mime_type": "application/pdf",
                "file_size_bytes": 2048,
                "upload_status": "UPLOADED",
                "is_active": True,
                "created_at": "2030-01-01T00:00:00Z",
            }
        ],
    }


def test_asset_types_returns_catalog() -> None:
    response = client.get("/api/v1/assets/types")

    assert response.status_code == 200
    assert "BANK_RELATIONSHIP" in response.json()["supported_types"]


def test_asset_blueprint_returns_type_blueprints() -> None:
    response = client.get("/api/v1/assets/blueprint")

    assert response.status_code == 200
    assert response.json()["types"][0]["document_support"] is True
    bank_type = next(
        item for item in response.json()["types"] if item["container_type"] == "BANK_RELATIONSHIP"
    )
    bank_field_names = [field["name"] for field in bank_type["detail_fields"]]
    assert "state" in bank_field_names
    state_field = next(field for field in bank_type["detail_fields"] if field["name"] == "state")
    assert "Maharashtra" in state_field["enum_options"]


def test_asset_list_requires_authentication() -> None:
    response = client.get("/api/v1/assets", params={"profile_id": "profile-primary"})

    assert response.status_code == 401


def test_asset_list_returns_items(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_list_assets(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        assert auth_context.account.id == "account-123"
        assert kwargs["profile_id"] == "profile-primary"
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return {
            "items": [_build_asset_response()],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }

    monkeypatch.setattr(asset_routes, "list_assets", fake_list_assets)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get(
            "/api/v1/assets",
            headers={"Authorization": "Bearer access-token"},
            params={"profile_id": "profile-primary"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["institution_name"] == "Acme Bank"


def test_asset_create_returns_created_asset(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_create_asset(session, auth_context, payload):  # type: ignore[no-untyped-def]
        assert payload.container_type == "BANK_RELATIONSHIP"
        assert payload.profile_id == "profile-primary"
        return _build_asset_response()

    monkeypatch.setattr(asset_routes, "create_asset", fake_create_asset)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/assets",
            headers={"Authorization": "Bearer access-token"},
            json={
                "profile_id": "profile-primary",
                "container_type": "bank_relationship",
                "institution_name": "Acme Bank",
                "detail": {"account_type": "savings", "account_number": "1234567890"},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["container_type"] == "BANK_RELATIONSHIP"


def test_asset_update_requires_fields() -> None:
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.patch(
            "/api/v1/assets/asset-123",
            headers={"Authorization": "Bearer access-token"},
            json={"profile_id": "profile-primary"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "At least one asset field must be provided." in response.text


def test_asset_detail_returns_asset(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_get_asset(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["asset_id"] == "asset-123"
        return _build_asset_response()

    monkeypatch.setattr(asset_routes, "get_asset", fake_get_asset)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get(
            "/api/v1/assets/asset-123",
            headers={"Authorization": "Bearer access-token"},
            params={"profile_id": "profile-primary"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "asset-123"


def test_asset_delete_returns_soft_deleted_asset(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_delete_asset(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        response = _build_asset_response()
        response["is_active"] = False
        return response

    monkeypatch.setattr(asset_routes, "delete_asset", fake_delete_asset)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.delete(
            "/api/v1/assets/asset-123",
            headers={"Authorization": "Bearer access-token"},
            params={"profile_id": "profile-primary"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_active"] is False
