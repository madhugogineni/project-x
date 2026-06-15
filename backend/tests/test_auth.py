from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.dependencies.auth import get_current_account_context
from api.routes import auth as auth_routes
from app import app
from core.auth_configs import get_otp_flow_config, is_supported_otp_flow
from core.security import TokenValidationError, create_jwt, decode_jwt, hash_secret, verify_secret
from core.settings import Settings
from db.models import (
    Account,
    AccountAddress,
    AccountInactivityState,
    AccountPan,
    Profile,
    ProfileType,
)
from services import auth_service
from services.auth_service import AuthenticatedAccountContext

client = TestClient(app)
TEST_SECRET = "test-secret-key-which-is-definitely-long-enough"


def _build_auth_response() -> dict:
    return {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
        "access_token_expires_at": "2030-01-01T00:15:00Z",
        "refresh_token_expires_at": "2030-01-08T00:00:00Z",
        "account": {
            "id": "account-123",
            "email": "user@example.com",
            "phone": "919999999999",
            "full_name": "Test User",
            "email_verified": False,
            "phone_verified": True,
            "status": "ACTIVE",
            "primary_profile_id": "profile-123",
        },
    }


def _build_otp_response(flow: str = "LOGIN") -> dict:
    return {
        "otp_session_id": "otp-session-123",
        "expires_at": "2030-01-01T00:05:00Z",
        "flow": flow,
        "resend_count": 0,
        "remaining_resends": 2,
        "attempts_remaining": 5,
        "cooldown_until": None,
    }


def _build_signup_verification_response() -> dict:
    return {
        "verified_signup_token": "signup-proof-token",
        "expires_at": "2030-01-01T00:10:00Z",
    }


def _build_logout_response() -> dict:
    return {
        "revoked_access_token": True,
        "revoked_refresh_token": True,
    }


def _build_signup_complete_payload() -> dict:
    return {
        "verified_signup_token": "signup-proof-token",
        "email": "User@Example.com",
        "full_name": "Test User",
        "date_of_birth": "1995-06-15",
        "gender": "male",
        "pan_number": "abcde1234f",
        "name_on_pan": "Test User",
        "current_address": {
            "address_line_1": "123 Main Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "country": "India",
        },
        "is_same_as_current": True,
    }


def test_secret_hash_round_trip() -> None:
    secret = "123456"
    encoded_secret = hash_secret(secret)

    assert encoded_secret != secret
    assert verify_secret(secret, encoded_secret)
    assert not verify_secret("654321", encoded_secret)


def test_decode_jwt_rejects_invalid_signature() -> None:
    token, _claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
    )

    with pytest.raises(TokenValidationError, match="signature"):
        decode_jwt(
            token,
            secret_key="a-different-secret-key-which-is-also-long-enough",
            issuer="project-x-api",
            audience="project-x-clients",
        )


def test_decode_jwt_rejects_expired_tokens() -> None:
    token, _claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(TokenValidationError, match="expired"):
        decode_jwt(
            token,
            secret_key=TEST_SECRET,
            issuer="project-x-api",
            audience="project-x-clients",
        )


def test_settings_reject_non_numeric_local_otp() -> None:
    with pytest.raises(ValueError, match="LOCAL_OTP must contain digits only"):
        Settings(
            database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test_projectx",
            jwt_secret_key=TEST_SECRET,
            local_otp="12ab56",
        )


def test_settings_reject_mismatched_local_otp_length() -> None:
    with pytest.raises(ValueError, match="LOCAL_OTP must match OTP_LENGTH"):
        Settings(
            database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test_projectx",
            jwt_secret_key=TEST_SECRET,
            otp_length=4,
            local_otp="123456",
        )


def test_resolve_otp_code_uses_local_otp_in_local() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test_projectx",
        jwt_secret_key=TEST_SECRET,
        environment="local",
        local_otp="654321",
    )

    assert auth_service._resolve_otp_code(settings) == "654321"


def test_resolve_otp_code_generates_random_otp_outside_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/test_projectx",
        jwt_secret_key=TEST_SECRET,
        environment="development",
        local_otp="654321",
    )

    monkeypatch.setattr(auth_service, "generate_numeric_otp", lambda length: "112233")

    assert auth_service._resolve_otp_code(settings) == "112233"


def test_otp_flow_config_is_supported() -> None:
    assert is_supported_otp_flow("SIGNUP")
    assert is_supported_otp_flow("LOGIN")
    assert get_otp_flow_config("SIGNUP").requires_unique_phone is True
    assert get_otp_flow_config("LOGIN").requires_existing_account is True


def test_otp_request_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_request_otp(session, payload, request_context):  # type: ignore[no-untyped-def]
        assert payload.phone == "919999999999"
        assert payload.flow == "SIGNUP"
        assert request_context.user_agent == "pytest"
        return _build_otp_response("SIGNUP")

    monkeypatch.setattr(auth_routes, "request_otp", fake_request_otp)

    response = client.post(
        "/api/v1/auth/otp/request",
        headers={"user-agent": "pytest"},
        json={"phone": "+91 99999 99999", "flow": "signup"},
    )

    assert response.status_code == 200
    assert response.json()["otp_session_id"] == "otp-session-123"
    assert "debug_otp" not in response.json()


def test_signup_verify_otp_returns_verified_token(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_verify_otp(session, payload, request_context):  # type: ignore[no-untyped-def]
        assert payload.phone == "919999999999"
        assert payload.otp == "123456"
        assert payload.flow == "SIGNUP"
        assert request_context.user_agent == "pytest"
        return _build_signup_verification_response()

    monkeypatch.setattr(auth_routes, "verify_otp", fake_verify_otp)

    response = client.post(
        "/api/v1/auth/otp/verify",
        headers={"user-agent": "pytest"},
        json={
            "otp_session_id": "otp-session-123",
            "phone": "+91 99999 99999",
            "otp": "123456",
            "flow": "signup",
        },
    )

    assert response.status_code == 200
    assert response.json()["verified_signup_token"] == "signup-proof-token"


def test_signup_complete_rejects_missing_permanent_address() -> None:
    payload = _build_signup_complete_payload()
    payload["is_same_as_current"] = False

    response = client.post("/api/v1/auth/signup/complete", json=payload)

    assert response.status_code == 422
    assert "Permanent address is required" in response.json()["detail"][0]["msg"]


def test_signup_complete_returns_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_complete_signup(session, payload, request_context):  # type: ignore[no-untyped-def]
        assert payload.email == "user@example.com"
        assert payload.gender == "MALE"
        assert payload.pan_number == "ABCDE1234F"
        assert request_context.user_agent == "pytest"
        return _build_auth_response()

    monkeypatch.setattr(auth_routes, "complete_signup", fake_complete_signup)

    response = client.post(
        "/api/v1/auth/signup/complete",
        headers={"user-agent": "pytest"},
        json=_build_signup_complete_payload(),
    )

    assert response.status_code == 201
    assert response.json()["account"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_complete_signup_creates_default_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = auth_service.utc_now()
    otp_session = SimpleNamespace(
        id="otp-session-123",
        phone="919999999999",
        purpose="SIGNUP",
        consumed_at=None,
        verified_at=now,
        verified_expires_at=now + timedelta(minutes=10),
    )
    settings = auth_service.get_settings()
    verified_signup_token, _claims = create_jwt(
        subject=otp_session.id,
        token_type="SIGNUP_VERIFIED",
        secret_key=settings.jwt_secret_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=timedelta(minutes=10),
        additional_claims={"phone": otp_session.phone, "purpose": "SIGNUP"},
    )
    fake_session = _FakeAsyncSession(otp_session)

    async def fake_ensure_account_is_unique(session, *, email, phone):  # type: ignore[no-untyped-def]
        assert email == "user@example.com"
        assert phone == otp_session.phone

    async def fake_create_session_tokens(**kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["primary_profile_id"]
        return _build_auth_response()

    autolink_calls = []

    async def fake_autolink_nominee_records_for_account(
        session,
        *,
        account,
        nominee_profile_id,
        now,
    ):  # type: ignore[no-untyped-def]
        autolink_calls.append(
            {
                "account_id": account.id,
                "nominee_profile_id": nominee_profile_id,
                "now": now,
            }
        )

    monkeypatch.setattr(auth_service, "_ensure_account_is_unique", fake_ensure_account_is_unique)
    monkeypatch.setattr(auth_service, "_create_session_tokens", fake_create_session_tokens)
    monkeypatch.setattr(
        auth_service,
        "autolink_nominee_records_for_account",
        fake_autolink_nominee_records_for_account,
    )

    response = await auth_service.complete_signup(
        fake_session,
        SimpleNamespace(
            verified_signup_token=verified_signup_token,
            email="user@example.com",
            full_name="Test User",
            date_of_birth="1995-06-15",
            gender="male",
            pan_number="abcde1234f",
            name_on_pan="Test User",
            current_address=SimpleNamespace(
                address_line_1="123 Main Street",
                address_line_2=None,
                landmark=None,
                city="Mumbai",
                district=None,
                state="Maharashtra",
                pincode="400001",
                country="India",
            ),
            permanent_address=None,
            is_same_as_current=True,
        ),
        auth_service.AuthRequestContext(
            ip_address="127.0.0.1",
            user_agent="pytest",
            device_name="pixel",
        ),
    )

    assert response["account"]["phone"] == otp_session.phone
    assert otp_session.consumed_at is not None
    assert len(fake_session.added) == 7
    assert any(isinstance(item, Account) for item in fake_session.added)
    assert any(isinstance(item, AccountPan) for item in fake_session.added)
    assert any(isinstance(item, AccountInactivityState) for item in fake_session.added)
    assert {item.profile_type for item in fake_session.added if isinstance(item, Profile)} == {
        ProfileType.PRIMARY,
        ProfileType.NOMINEE,
    }
    assert {
        item.address_type for item in fake_session.added if isinstance(item, AccountAddress)
    } == {"CURRENT", "PERMANENT"}
    assert len(autolink_calls) == 1


@pytest.mark.asyncio
async def test_complete_signup_rejects_replayed_consumed_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = auth_service.utc_now()
    otp_session = SimpleNamespace(
        id="otp-session-123",
        phone="919999999999",
        purpose="SIGNUP",
        consumed_at=now,
        verified_at=now,
        verified_expires_at=now + timedelta(minutes=10),
    )
    settings = auth_service.get_settings()
    verified_signup_token, _claims = create_jwt(
        subject=otp_session.id,
        token_type="SIGNUP_VERIFIED",
        secret_key=settings.jwt_secret_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=timedelta(minutes=10),
        additional_claims={"phone": otp_session.phone, "purpose": "SIGNUP"},
    )
    fake_session = _FakeAsyncSession(otp_session)

    async def fake_ensure_account_is_unique(session, *, email, phone):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(auth_service, "_ensure_account_is_unique", fake_ensure_account_is_unique)

    with pytest.raises(auth_service.HTTPException, match="already been used"):
        await auth_service.complete_signup(
            fake_session,
            SimpleNamespace(
                verified_signup_token=verified_signup_token,
                email="user@example.com",
                full_name="Test User",
                date_of_birth="1995-06-15",
                gender="MALE",
                pan_number="ABCDE1234F",
                name_on_pan="Test User",
                current_address=SimpleNamespace(
                    address_line_1="123 Main Street",
                    address_line_2=None,
                    landmark=None,
                    city="Mumbai",
                    district=None,
                    state="Maharashtra",
                    pincode="400001",
                    country="India",
                ),
                permanent_address=None,
                is_same_as_current=True,
            ),
            auth_service.AuthRequestContext(
                ip_address=None,
                user_agent=None,
                device_name=None,
            ),
        )


@pytest.mark.asyncio
async def test_complete_signup_rejects_expired_signup_proof() -> None:
    settings = auth_service.get_settings()
    expired_token, _claims = create_jwt(
        subject="otp-session-123",
        token_type="SIGNUP_VERIFIED",
        secret_key=settings.jwt_secret_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=timedelta(seconds=-1),
        additional_claims={"phone": "919999999999", "purpose": "SIGNUP"},
    )

    with pytest.raises(auth_service.HTTPException, match="expired"):
        await auth_service.complete_signup(
            _FakeAsyncSession(),
            SimpleNamespace(
                verified_signup_token=expired_token,
                email="user@example.com",
                full_name="Test User",
                date_of_birth="1995-06-15",
                gender="MALE",
                pan_number="ABCDE1234F",
                name_on_pan="Test User",
                current_address=SimpleNamespace(
                    address_line_1="123 Main Street",
                    address_line_2=None,
                    landmark=None,
                    city="Mumbai",
                    district=None,
                    state="Maharashtra",
                    pincode="400001",
                    country="India",
                ),
                permanent_address=None,
                is_same_as_current=True,
            ),
            auth_service.AuthRequestContext(
                ip_address=None,
                user_agent=None,
                device_name=None,
            ),
        )


@pytest.mark.asyncio
async def test_complete_signup_rejects_duplicate_identity_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = auth_service.utc_now()
    otp_session = SimpleNamespace(
        id="otp-session-123",
        phone="919999999999",
        purpose="SIGNUP",
        consumed_at=None,
        verified_at=now,
        verified_expires_at=now + timedelta(minutes=10),
    )
    settings = auth_service.get_settings()
    verified_signup_token, _claims = create_jwt(
        subject=otp_session.id,
        token_type="SIGNUP_VERIFIED",
        secret_key=settings.jwt_secret_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        expires_delta=timedelta(minutes=10),
        additional_claims={"phone": otp_session.phone, "purpose": "SIGNUP"},
    )
    fake_session = _FakeAsyncSession(otp_session)

    async def fake_ensure_account_is_unique(session, *, email, phone):  # type: ignore[no-untyped-def]
        raise auth_service._conflict_error("An account with this email already exists.")

    monkeypatch.setattr(auth_service, "_ensure_account_is_unique", fake_ensure_account_is_unique)

    with pytest.raises(auth_service.HTTPException, match="already exists"):
        await auth_service.complete_signup(
            fake_session,
            SimpleNamespace(
                verified_signup_token=verified_signup_token,
                email="user@example.com",
                full_name="Test User",
                date_of_birth="1995-06-15",
                gender="MALE",
                pan_number="ABCDE1234F",
                name_on_pan="Test User",
                current_address=SimpleNamespace(
                    address_line_1="123 Main Street",
                    address_line_2=None,
                    landmark=None,
                    city="Mumbai",
                    district=None,
                    state="Maharashtra",
                    pincode="400001",
                    country="India",
                ),
                permanent_address=None,
                is_same_as_current=True,
            ),
            auth_service.AuthRequestContext(
                ip_address=None,
                user_agent=None,
                device_name=None,
            ),
        )


def test_login_request_otp_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_request_otp(session, payload, request_context):  # type: ignore[no-untyped-def]
        assert payload.phone == "919999999999"
        assert payload.flow == "LOGIN"
        assert request_context.user_agent == "pytest"
        return _build_otp_response()

    monkeypatch.setattr(auth_routes, "request_otp", fake_request_otp)

    response = client.post(
        "/api/v1/auth/otp/request",
        headers={"user-agent": "pytest"},
        json={"phone": "+91 99999 99999", "flow": "login"},
    )

    assert response.status_code == 200
    assert response.json()["flow"] == "LOGIN"
    assert "debug_otp" not in response.json()


def test_login_verify_otp_returns_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_verify_otp(session, payload, request_context):  # type: ignore[no-untyped-def]
        assert payload.phone == "919999999999"
        assert payload.otp == "654321"
        assert payload.flow == "LOGIN"
        assert request_context.device_name == "iPhone 15"
        return _build_auth_response()

    monkeypatch.setattr(auth_routes, "verify_otp", fake_verify_otp)

    response = client.post(
        "/api/v1/auth/otp/verify",
        headers={"x-device-name": "iPhone 15"},
        json={
            "otp_session_id": "otp-session-123",
            "phone": "919999999999",
            "otp": "654321",
            "flow": "login",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access-token"


def test_request_otp_creates_new_session_when_none_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_acquire_otp_flow_lock(session, phone, flow):  # type: ignore[no-untyped-def]
        assert phone == "919999999999"
        assert flow == "SIGNUP"

    async def fake_validate_otp_flow_prerequisites(session, phone, flow_config):  # type: ignore[no-untyped-def]
        assert phone == "919999999999"
        assert flow_config.requires_existing_account is False

    async def fake_get_latest_pending_otp_session(**_kwargs):  # type: ignore[no-untyped-def]
        return None

    async def fake_create_otp_session(**kwargs):  # type: ignore[no-untyped-def]
        assert kwargs["phone"] == "919999999999"
        assert kwargs["flow"] == "SIGNUP"
        return _build_otp_response("SIGNUP")

    monkeypatch.setattr(auth_service, "_acquire_otp_flow_lock", fake_acquire_otp_flow_lock)
    monkeypatch.setattr(
        auth_service,
        "_validate_otp_flow_prerequisites",
        fake_validate_otp_flow_prerequisites,
    )
    monkeypatch.setattr(
        auth_service,
        "_get_latest_pending_otp_session",
        fake_get_latest_pending_otp_session,
    )
    monkeypatch.setattr(auth_service, "_create_otp_session", fake_create_otp_session)

    response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "+91 99999 99999", "flow": "signup"},
    )

    assert response.status_code == 200
    assert response.json()["flow"] == "SIGNUP"


def test_request_otp_returns_cooldown_when_resends_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_acquire_otp_flow_lock(session, phone, flow):  # type: ignore[no-untyped-def]
        assert flow == "LOGIN"

    async def fake_validate_otp_flow_prerequisites(session, phone, flow_config):  # type: ignore[no-untyped-def]
        return None

    async def fake_get_latest_pending_otp_session(**_kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(
            resend_count=2,
            max_resends=2,
            attempts=1,
            max_attempts=5,
            expires_at=auth_service.utc_now() + timedelta(minutes=1),
            cooldown_until=None,
            consumed_at=None,
            verified_at=None,
            purpose="LOGIN",
            id="otp-session-123",
        )

    async def fake_create_otp_session(**_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("Should not create a new session while cooldown is set.")

    monkeypatch.setattr(auth_service, "_acquire_otp_flow_lock", fake_acquire_otp_flow_lock)
    monkeypatch.setattr(
        auth_service,
        "_validate_otp_flow_prerequisites",
        fake_validate_otp_flow_prerequisites,
    )
    monkeypatch.setattr(
        auth_service,
        "_get_latest_pending_otp_session",
        fake_get_latest_pending_otp_session,
    )
    monkeypatch.setattr(auth_service, "_create_otp_session", fake_create_otp_session)

    response = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "919999999999", "flow": "login"},
    )

    assert response.status_code == 429
    assert "already sent" in response.json()["detail"]


def test_verify_otp_rejects_incorrect_otp_length() -> None:
    response = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "otp_session_id": "otp-session-123",
            "phone": "919999999999",
            "otp": "12345",
            "flow": "login",
        },
    )

    assert response.status_code == 422
    assert "exactly 6 digits" in response.json()["detail"][0]["msg"]


class _FakeAsyncSession:
    def __init__(self, otp_session=None, *, scalar_result=None, scalars_result=None):
        self.otp_session = otp_session
        self.scalar_result = otp_session if scalar_result is None else scalar_result
        self.scalars_result = list(scalars_result or [])
        self.flushed = False
        self.committed = False
        self.added = []

    async def scalar(self, statement, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        if getattr(statement, "_for_update_arg", None) is None:
            raise AssertionError("Expected row-level locking for signup completion.")
        return self.scalar_result

    async def scalars(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return _FakeScalarResult(self.scalars_result)

    async def get(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return self.otp_session

    def add_all(self, items):  # type: ignore[no-untyped-def]
        self.added.extend(items)

    async def flush(self) -> None:
        for item in self.added:
            if hasattr(item, "id") and item.id is None:
                item.id = str(uuid4())
        self.flushed = True

    async def commit(self) -> None:
        self.committed = True


class _FakeScalarResult:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


@pytest.mark.asyncio
async def test_get_token_record_for_update_uses_row_lock() -> None:
    token_record = SimpleNamespace(jti="refresh-jti", token_type="REFRESH")
    fake_session = _FakeAsyncSession(scalar_result=token_record)

    record = await auth_service._get_token_record_for_update(
        fake_session,
        "refresh-jti",
        "REFRESH",
    )

    assert record is token_record


@pytest.mark.asyncio
async def test_create_session_tokens_uses_shared_session_id() -> None:
    account = SimpleNamespace(
        id="account-123",
        email="user@example.com",
        phone="919999999999",
        full_name="Test User",
        email_verified=False,
        phone_verified=True,
        status="ACTIVE",
    )
    fake_session = _FakeAsyncSession()

    response = await auth_service._create_session_tokens(
        session=fake_session,
        account=account,
        primary_profile_id="profile-123",
        session_id="session-123",
        request_context=auth_service.AuthRequestContext(
            ip_address="127.0.0.1",
            user_agent="pytest",
            device_name="pixel",
        ),
    )

    assert response.account.primary_profile_id == "profile-123"
    assert len(fake_session.added) == 2
    assert fake_session.added[0].session_id == "session-123"
    assert fake_session.added[1].session_id == "session-123"

    access_claims = decode_jwt(
        response.access_token,
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expected_token_type="ACCESS",
    )
    refresh_claims = decode_jwt(
        response.refresh_token,
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expected_token_type="REFRESH",
    )
    assert access_claims.extra_claims["session_id"] == "session-123"
    assert refresh_claims.extra_claims["session_id"] == "session-123"


@pytest.mark.asyncio
async def test_refresh_session_rotates_with_same_session_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = auth_service.utc_now()
    refresh_record = SimpleNamespace(
        jti="refresh-jti",
        session_id="session-123",
        account_id="account-123",
        revoked_at=None,
        expires_at=now + timedelta(minutes=5),
        last_used_at=None,
        token_type="REFRESH",
    )
    account = SimpleNamespace(
        id="account-123",
        status="ACTIVE",
        deleted_at=None,
    )
    primary_profile = SimpleNamespace(id="profile-123")
    inactivity_state = SimpleNamespace(last_active_at=None)
    fake_session = _FakeAsyncSession(otp_session=account)
    captured = {}

    async def fake_get_token_record_for_update(session, jti, token_type):  # type: ignore[no-untyped-def]
        assert jti == refresh_claims.jti
        assert token_type == "REFRESH"
        return refresh_record

    async def fake_ensure_default_profiles(session, account_arg):  # type: ignore[no-untyped-def]
        assert account_arg is account
        return primary_profile, SimpleNamespace(id="nominee-profile-123")

    async def fake_ensure_inactivity_state(session, account_id, last_active_at):  # type: ignore[no-untyped-def]
        assert account_id == "account-123"
        inactivity_state.last_active_at = last_active_at
        return inactivity_state

    async def fake_create_session_tokens(**kwargs):  # type: ignore[no-untyped-def]
        captured["session_id"] = kwargs["session_id"]
        return _build_auth_response()

    monkeypatch.setattr(
        auth_service,
        "_get_token_record_for_update",
        fake_get_token_record_for_update,
    )
    monkeypatch.setattr(
        auth_service,
        "_ensure_default_profiles",
        fake_ensure_default_profiles,
    )
    monkeypatch.setattr(
        auth_service,
        "_ensure_inactivity_state",
        fake_ensure_inactivity_state,
    )
    monkeypatch.setattr(auth_service, "_create_session_tokens", fake_create_session_tokens)

    refresh_token, refresh_claims = create_jwt(
        subject="account-123",
        token_type="REFRESH",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123", "session_id": "session-123"},
    )
    refresh_record.jti = refresh_claims.jti

    response = await auth_service.refresh_session(
        fake_session,
        refresh_token,
        auth_service.AuthRequestContext(
            ip_address="127.0.0.1",
            user_agent="pytest",
            device_name="pixel",
        ),
    )

    assert response["refresh_token"] == "refresh-token"
    assert refresh_record.revoked_at is not None
    assert captured["session_id"] == "session-123"
    assert refresh_claims.jti == refresh_record.jti


@pytest.mark.asyncio
async def test_logout_account_revokes_current_and_matching_refresh_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = auth_service.utc_now()
    access_record = SimpleNamespace(
        jti="access-jti",
        session_id="session-123",
        account_id="account-123",
        revoked_at=None,
        expires_at=now + timedelta(minutes=5),
        last_used_at=None,
        token_type="ACCESS",
    )
    refresh_record = SimpleNamespace(
        jti="refresh-jti",
        session_id="session-123",
        account_id="account-123",
        revoked_at=None,
        expires_at=now + timedelta(days=7),
        last_used_at=None,
        token_type="REFRESH",
    )
    _access_token, access_claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123", "session_id": "session-123"},
    )
    refresh_token, refresh_claims = create_jwt(
        subject="account-123",
        token_type="REFRESH",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(days=7),
        additional_claims={"profile_id": "profile-123", "session_id": "session-123"},
    )
    access_record.jti = access_claims.jti
    refresh_record.jti = refresh_claims.jti
    auth_context = AuthenticatedAccountContext(
        account=SimpleNamespace(id="account-123"),
        profile_id="profile-123",
        claims=access_claims,
        session_id="session-123",
    )
    fake_session = _FakeAsyncSession()

    async def fake_get_token_record_for_update(session, jti, token_type):  # type: ignore[no-untyped-def]
        if token_type == "ACCESS":
            assert jti == access_claims.jti
            return access_record
        assert jti == refresh_claims.jti
        return refresh_record

    monkeypatch.setattr(
        auth_service,
        "_get_token_record_for_update",
        fake_get_token_record_for_update,
    )

    response = await auth_service.logout_account(
        fake_session,
        auth_context,
        refresh_token,
    )

    assert response.revoked_access_token is True
    assert response.revoked_refresh_token is True
    assert access_record.revoked_at is not None
    assert refresh_record.revoked_at is not None
    assert access_claims.jti == access_record.jti
    assert refresh_claims.jti == refresh_record.jti


@pytest.mark.asyncio
async def test_logout_account_rejects_mismatched_refresh_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = auth_service.utc_now()
    access_record = SimpleNamespace(
        jti="access-jti",
        session_id="session-123",
        account_id="account-123",
        revoked_at=None,
        expires_at=now + timedelta(minutes=5),
        last_used_at=None,
        token_type="ACCESS",
    )
    auth_context = AuthenticatedAccountContext(
        account=SimpleNamespace(id="account-123"),
        profile_id="profile-123",
        claims=create_jwt(
            subject="account-123",
            token_type="ACCESS",
            secret_key=TEST_SECRET,
            issuer="project-x-api",
            audience="project-x-clients",
            expires_delta=timedelta(minutes=5),
            additional_claims={"profile_id": "profile-123", "session_id": "session-123"},
        )[1],
        session_id="session-123",
    )

    async def fake_get_token_record_for_update(session, jti, token_type):  # type: ignore[no-untyped-def]
        assert token_type == "ACCESS"
        return access_record

    monkeypatch.setattr(
        auth_service,
        "_get_token_record_for_update",
        fake_get_token_record_for_update,
    )

    refresh_token = create_jwt(
        subject="account-123",
        token_type="REFRESH",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(days=7),
        additional_claims={"profile_id": "profile-123", "session_id": "session-other"},
    )[0]

    with pytest.raises(auth_service.HTTPException, match="Token session is invalid"):
        await auth_service.logout_account(
            _FakeAsyncSession(),
            auth_context,
            refresh_token,
        )


@pytest.mark.asyncio
async def test_get_current_authenticated_account_returns_session_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = auth_service.utc_now()
    account = SimpleNamespace(
        id="account-123",
        email="user@example.com",
        phone="919999999999",
        full_name="Test User",
        email_verified=False,
        phone_verified=True,
        status="ACTIVE",
        deleted_at=None,
    )
    token_record = SimpleNamespace(
        jti="access-jti",
        session_id="session-123",
        account_id="account-123",
        revoked_at=None,
        expires_at=now + timedelta(minutes=5),
        active_profile_id="profile-123",
        last_used_at=None,
    )
    inactivity_state = SimpleNamespace(last_active_at=None)

    async def fake_get_token_record_for_update(session, jti, token_type):  # type: ignore[no-untyped-def]
        assert token_type == "ACCESS"
        return token_record

    async def fake_get(session, model, pk):  # type: ignore[no-untyped-def]
        assert model is Account
        assert pk == "account-123"
        return account

    async def fake_ensure_inactivity_state(session, account_id, last_active_at):  # type: ignore[no-untyped-def]
        inactivity_state.last_active_at = last_active_at
        return inactivity_state

    monkeypatch.setattr(
        auth_service,
        "_get_token_record_for_update",
        fake_get_token_record_for_update,
    )
    monkeypatch.setattr(_FakeAsyncSession, "get", fake_get, raising=False)
    monkeypatch.setattr(
        auth_service,
        "_ensure_inactivity_state",
        fake_ensure_inactivity_state,
    )

    claims_token = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123", "session_id": "session-123"},
    )[0]

    context = await auth_service.get_current_authenticated_account(
        _FakeAsyncSession(otp_session=account),
        claims_token,
    )

    assert context.profile_id == "profile-123"
    assert context.session_id == "session-123"
    assert token_record.last_used_at is not None
    assert inactivity_state.last_active_at is not None


@pytest.mark.asyncio
async def test_list_account_sessions_groups_logical_sessions() -> None:
    now = auth_service.utc_now()
    current_claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123", "session_id": "session-current"},
    )[1]
    auth_context = AuthenticatedAccountContext(
        account=SimpleNamespace(id="account-123"),
        profile_id="profile-123",
        claims=current_claims,
        session_id="session-current",
    )
    rows = [
        SimpleNamespace(
            id="row-1",
            session_id="session-current",
            jti="access-current",
            token_type="ACCESS",
            device_name="Pixel",
            ip_address="127.0.0.1",
            user_agent="Chrome",
            expires_at=now + timedelta(minutes=5),
            revoked_at=None,
            last_used_at=now,
            created_at=now - timedelta(minutes=10),
            active_profile_id="profile-123",
        ),
        SimpleNamespace(
            id="row-2",
            session_id="session-current",
            jti="refresh-current",
            token_type="REFRESH",
            device_name="Pixel",
            ip_address="127.0.0.1",
            user_agent="Chrome",
            expires_at=now + timedelta(days=7),
            revoked_at=None,
            last_used_at=now - timedelta(minutes=1),
            created_at=now - timedelta(minutes=10),
            active_profile_id="profile-123",
        ),
        SimpleNamespace(
            id="row-3",
            session_id="session-old",
            jti="refresh-old",
            token_type="REFRESH",
            device_name="Laptop",
            ip_address="10.0.0.2",
            user_agent="Firefox",
            expires_at=now + timedelta(days=7),
            revoked_at=None,
            last_used_at=now - timedelta(hours=1),
            created_at=now - timedelta(days=1),
            active_profile_id="profile-123",
        ),
        SimpleNamespace(
            id="row-4",
            session_id="session-old",
            jti="access-old",
            token_type="ACCESS",
            device_name="Laptop",
            ip_address="10.0.0.2",
            user_agent="Firefox",
            expires_at=now + timedelta(minutes=5),
            revoked_at=None,
            last_used_at=now - timedelta(minutes=30),
            created_at=now - timedelta(days=1),
            active_profile_id="profile-123",
        ),
    ]

    sessions = await auth_service.list_account_sessions(
        _FakeAsyncSession(scalars_result=rows),
        auth_context,
        limit=20,
        offset=0,
    )

    assert {session.session_id for session in sessions.items} == {
        "session-current",
        "session-old",
    }
    current_session = next(
        session for session in sessions.items if session.session_id == "session-current"
    )
    other_session = next(
        session for session in sessions.items if session.session_id == "session-old"
    )
    assert current_session.token_type == "ACCESS"
    assert other_session.token_type == "REFRESH"
    assert current_session.id == "session-current"


@pytest.mark.asyncio
async def test_revoke_account_session_revokes_all_rows_and_blocks_self_revoke() -> None:
    now = auth_service.utc_now()
    auth_context = AuthenticatedAccountContext(
        account=SimpleNamespace(id="account-123"),
        profile_id="profile-123",
        claims=create_jwt(
            subject="account-123",
            token_type="ACCESS",
            secret_key=TEST_SECRET,
            issuer="project-x-api",
            audience="project-x-clients",
            expires_delta=timedelta(minutes=5),
            additional_claims={"profile_id": "profile-123", "session_id": "session-current"},
        )[1],
        session_id="session-current",
    )
    rows = [
        SimpleNamespace(
            session_id="session-target",
            revoked_at=None,
            expires_at=now + timedelta(minutes=5),
            revoke_reason=None,
            last_used_at=None,
        ),
        SimpleNamespace(
            session_id="session-target",
            revoked_at=None,
            expires_at=now + timedelta(days=7),
            revoke_reason=None,
            last_used_at=None,
        ),
    ]
    fake_session = _FakeAsyncSession(scalars_result=rows)

    response = await auth_service.revoke_account_session(
        fake_session,
        auth_context,
        "session-target",
    )

    assert response.revoked_access_token is True
    assert response.revoked_refresh_token is True
    assert all(row.revoked_at is not None for row in rows)

    with pytest.raises(auth_service.HTTPException, match="Current session cannot be revoked"):
        await auth_service.revoke_account_session(fake_session, auth_context, "session-current")


@pytest.mark.asyncio
async def test_verify_otp_login_consumes_session_and_returns_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otp_session = SimpleNamespace(
        id="otp-session-123",
        phone="919999999999",
        purpose="LOGIN",
        consumed_at=None,
        verified_at=None,
        verified_expires_at=None,
        expires_at=auth_service.utc_now() + timedelta(minutes=5),
        attempts=0,
        max_attempts=5,
        otp_hash=hash_secret("654321"),
    )
    account = SimpleNamespace(
        id="account-123",
        status="ACTIVE",
        deleted_at=None,
        phone_verified=False,
        last_login_at=None,
    )
    primary_profile = SimpleNamespace(id="profile-123")
    inactivity_state = SimpleNamespace(last_active_at=None)
    captured = {}

    async def fake_verify_otp_session(**_kwargs):  # type: ignore[no-untyped-def]
        return otp_session

    async def fake_get_active_account_by_phone(session, phone):  # type: ignore[no-untyped-def]
        assert phone == "919999999999"
        return account

    async def fake_ensure_default_profiles(session, account_arg):  # type: ignore[no-untyped-def]
        assert account_arg is account
        return primary_profile, SimpleNamespace(id="nominee-profile-123")

    async def fake_ensure_inactivity_state(session, account_id, last_active_at):  # type: ignore[no-untyped-def]
        assert account_id == "account-123"
        inactivity_state.last_active_at = last_active_at
        return inactivity_state

    async def fake_create_session_tokens(**kwargs):  # type: ignore[no-untyped-def]
        account_arg = kwargs["account"]
        primary_profile_id = kwargs["primary_profile_id"]
        request_context = kwargs["request_context"]
        assert account_arg is account
        captured["primary_profile_id"] = primary_profile_id
        captured["device_name"] = request_context.device_name
        return _build_auth_response()

    monkeypatch.setattr(auth_service, "_verify_otp_session", fake_verify_otp_session)
    monkeypatch.setattr(
        auth_service,
        "_get_active_account_by_phone",
        fake_get_active_account_by_phone,
    )
    monkeypatch.setattr(
        auth_service,
        "_ensure_default_profiles",
        fake_ensure_default_profiles,
    )
    monkeypatch.setattr(
        auth_service,
        "_ensure_inactivity_state",
        fake_ensure_inactivity_state,
    )
    monkeypatch.setattr(auth_service, "_create_session_tokens", fake_create_session_tokens)

    response = await auth_service.verify_otp(
        _FakeAsyncSession(),
        SimpleNamespace(
            otp_session_id="otp-session-123",
            phone="919999999999",
            otp="654321",
            flow="LOGIN",
        ),
        auth_service.AuthRequestContext(
            ip_address="127.0.0.1",
            user_agent="pytest",
            device_name="pixel",
        ),
    )

    assert response["access_token"] == "access-token"
    assert otp_session.consumed_at is not None
    assert account.phone_verified is True
    assert account.last_login_at is not None
    assert captured["primary_profile_id"] == "profile-123"
    assert captured["device_name"] == "pixel"


@pytest.mark.asyncio
async def test_verify_otp_login_missing_account_returns_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otp_session = SimpleNamespace(
        id="otp-session-123",
        phone="919999999999",
        purpose="LOGIN",
        consumed_at=None,
        verified_at=None,
        verified_expires_at=None,
        expires_at=auth_service.utc_now() + timedelta(minutes=5),
        attempts=0,
        max_attempts=5,
        otp_hash=hash_secret("654321"),
    )

    async def fake_verify_otp_session(**_kwargs):  # type: ignore[no-untyped-def]
        return otp_session

    async def fake_get_active_account_by_phone(session, phone):  # type: ignore[no-untyped-def]
        raise auth_service.HTTPException(
            status_code=404,
            detail="No active account exists for this phone number.",
        )

    monkeypatch.setattr(auth_service, "_verify_otp_session", fake_verify_otp_session)
    monkeypatch.setattr(
        auth_service,
        "_get_active_account_by_phone",
        fake_get_active_account_by_phone,
    )

    with pytest.raises(auth_service.HTTPException, match="No active account exists"):
        await auth_service.verify_otp(
            _FakeAsyncSession(),
            SimpleNamespace(
                otp_session_id="otp-session-123",
                phone="919999999999",
                otp="654321",
                flow="LOGIN",
            ),
            auth_service.AuthRequestContext(
                ip_address=None,
                user_agent=None,
                device_name=None,
            ),
        )


@pytest.mark.asyncio
async def test_verify_otp_signup_reissues_token_while_window_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otp_session = SimpleNamespace(
        id="otp-session-123",
        phone="919999999999",
        purpose="SIGNUP",
        consumed_at=None,
        verified_at=auth_service.utc_now(),
        verified_expires_at=auth_service.utc_now() + timedelta(minutes=10),
    )

    async def fake_verify_otp_session(**_kwargs):  # type: ignore[no-untyped-def]
        return otp_session

    monkeypatch.setattr(auth_service, "_verify_otp_session", fake_verify_otp_session)

    response = await auth_service.verify_otp(
        _FakeAsyncSession(),
        SimpleNamespace(
            otp_session_id="otp-session-123",
            phone="919999999999",
            otp="123456",
            flow="SIGNUP",
        ),
        auth_service.AuthRequestContext(
            ip_address=None,
            user_agent=None,
            device_name=None,
        ),
    )

    assert response.verified_signup_token
    assert response.expires_at > auth_service.utc_now()


@pytest.mark.asyncio
async def test_verify_otp_bad_login_attempt_increments_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    otp_session = SimpleNamespace(
        id="otp-session-123",
        phone="919999999999",
        purpose="LOGIN",
        consumed_at=None,
        verified_at=None,
        verified_expires_at=None,
        expires_at=auth_service.utc_now() + timedelta(minutes=5),
        attempts=0,
        max_attempts=5,
        otp_hash=hash_secret("111111"),
    )
    fake_session = _FakeAsyncSession(otp_session)

    monkeypatch.setattr(auth_service, "verify_secret", lambda otp, stored: False)

    with pytest.raises(auth_service.HTTPException, match="OTP is invalid"):
        await auth_service._verify_otp_session(
            session=fake_session,
            otp_session_id="otp-session-123",
            phone="919999999999",
            otp="654321",
            flow="LOGIN",
        )

    assert otp_session.attempts == 1
    assert fake_session.flushed is True


def test_refresh_returns_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_refresh_session(session, refresh_token, request_context):  # type: ignore[no-untyped-def]
        assert refresh_token == "refresh-token"
        assert request_context.user_agent == "pytest"
        return _build_auth_response()

    monkeypatch.setattr(auth_routes, "refresh_session", fake_refresh_session)

    response = client.post(
        "/api/v1/auth/refresh",
        headers={"user-agent": "pytest"},
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] == "refresh-token"


def test_logout_requires_authentication() -> None:
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


def test_logout_revokes_current_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    _, claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123"},
    )

    async def override_current_account_context() -> AuthenticatedAccountContext:
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
        )

    async def fake_logout_account(session, auth_context, refresh_token):  # type: ignore[no-untyped-def]
        assert auth_context.claims.jti == claims.jti
        assert refresh_token == "refresh-token"
        return _build_logout_response()

    monkeypatch.setattr(auth_routes, "logout_account", fake_logout_account)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer access-token"},
            json={"refresh_token": "refresh-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["revoked_access_token"] is True
    assert response.json()["revoked_refresh_token"] is True


def test_me_requires_authentication() -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


def test_sessions_returns_paginated_items(monkeypatch: pytest.MonkeyPatch) -> None:
    _, claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123", "session_id": "session-123"},
    )

    async def override_current_account_context() -> AuthenticatedAccountContext:
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

    async def fake_list_account_sessions(session, auth_context, *, limit, offset):  # type: ignore[no-untyped-def]
        assert auth_context.account.id == "account-123"
        assert limit == 20
        assert offset == 0
        return {
            "items": [
                {
                    "id": "session-123",
                    "session_id": "session-123",
                    "jti": "token-123",
                    "token_type": "ACCESS",
                    "device_name": "MacBook",
                    "ip_address": "127.0.0.1",
                    "user_agent": "pytest",
                    "revoked_at": None,
                    "last_used_at": "2030-01-01T00:00:00Z",
                    "created_at": "2030-01-01T00:00:00Z",
                    "active_profile_id": "profile-123",
                }
            ],
            "total": 1,
            "limit": 20,
            "offset": 0,
            "has_more": False,
        }

    monkeypatch.setattr(auth_routes, "list_account_sessions", fake_list_account_sessions)
    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get(
            "/api/v1/auth/sessions",
            headers={"Authorization": "Bearer access-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["session_id"] == "session-123"


def test_me_returns_current_account() -> None:
    _, claims = create_jwt(
        subject="account-123",
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": "profile-123"},
    )

    async def override_current_account_context() -> AuthenticatedAccountContext:
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
        )

    app.dependency_overrides[get_current_account_context] = override_current_account_context
    try:
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer access-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["primary_profile_id"] == "profile-123"
