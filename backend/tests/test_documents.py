from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.dependencies.auth import get_current_account_context
from api.routes import documents as document_routes
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


def _build_document_response() -> dict:
    return {
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


def test_asset_document_list_requires_authentication() -> None:
    response = client.get(
        "/api/v1/assets/asset-123/documents",
        params={"profile_id": "profile-primary"},
    )

    assert response.status_code == 401


def test_asset_document_list_returns_rows(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_list_asset_documents(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["asset_id"] == "asset-123"
        assert kwargs["limit"] == 20
        assert kwargs["offset"] == 0
        return {
            "items": [_build_document_response()],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }

    monkeypatch.setattr(document_routes, "list_asset_documents", fake_list_asset_documents)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get(
            "/api/v1/assets/asset-123/documents",
            headers={"Authorization": "Bearer access-token"},
            params={"profile_id": "profile-primary"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["document_type"] == "ACCOUNT_STATEMENT"


def test_document_initiate_upload_returns_presigned_payload(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_initiate_document_upload(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        payload = kwargs["payload"]
        assert payload.document_type == "ACCOUNT_STATEMENT"
        return {
            "document_id": "doc-123",
            "upload_url": "https://upload.example.com",
            "upload_headers": {"Content-Type": "application/pdf"},
            "expires_at": "2030-01-01T00:10:00Z",
        }

    monkeypatch.setattr(
        document_routes,
        "initiate_document_upload",
        fake_initiate_document_upload,
    )
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/assets/asset-123/documents/initiate-upload",
            headers={"Authorization": "Bearer access-token"},
            json={
                "profile_id": "profile-primary",
                "document_type": "account_statement",
                "original_file_name": "statement.pdf",
                "mime_type": "application/pdf",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["document_id"] == "doc-123"


def test_document_complete_upload_returns_metadata(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_complete_document_upload(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["asset_id"] == "asset-123"
        assert kwargs["document_id"] == "doc-123"
        return _build_document_response()

    monkeypatch.setattr(
        document_routes,
        "complete_document_upload",
        fake_complete_document_upload,
    )
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/assets/asset-123/documents/complete-upload",
            headers={"Authorization": "Bearer access-token"},
            json={"profile_id": "profile-primary", "document_id": "doc-123"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "doc-123"


def test_document_download_url_returns_signed_url(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def override_current_account_context() -> AuthenticatedAccountContext:
        return _build_auth_context()

    async def fake_get_document_download_url(session, auth_context, **kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["document_id"] == "doc-123"
        return {
            "download_url": "https://download.example.com",
            "expires_at": "2030-01-01T00:10:00Z",
        }

    monkeypatch.setattr(
        document_routes,
        "get_document_download_url",
        fake_get_document_download_url,
    )
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/documents/doc-123/download-url",
            headers={"Authorization": "Bearer access-token"},
            params={"profile_id": "profile-primary"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["download_url"] == "https://download.example.com"
