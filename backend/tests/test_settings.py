import json
import os
import sys
from types import SimpleNamespace

import pytest

from core.settings import get_settings, reset_settings_cache

TEST_SECRET = "test-secret-key-which-is-definitely-long-enough"


@pytest.fixture(autouse=True)
def reset_cached_settings() -> None:
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_get_settings_skips_aws_secrets_in_local(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_client(_service_name: str, **_kwargs):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("AWS Secrets Manager should not be called in local.")

    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("AWS_SECRETS_MANAGER_SECRET_ID", "project-x/local/backend")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=fake_client))

    settings = get_settings()

    assert settings.environment == "local"
    assert called is False


def test_get_settings_loads_aws_secret_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeSecretsManagerClient:
        def get_secret_value(self, **kwargs: str) -> dict[str, str]:
            captured["secret_id"] = kwargs["SecretId"]
            return {
                "SecretString": json.dumps(
                    {
                        "DATABASE_URL": "postgresql+asyncpg://secret-user:secret-pass@db:5432/app",
                        "JWT_SECRET_KEY": TEST_SECRET,
                        "LOCAL_OTP": "654321",
                    }
                )
            }

    def fake_client(service_name: str, **kwargs: str) -> FakeSecretsManagerClient:
        captured["service_name"] = service_name
        captured["kwargs"] = kwargs
        return FakeSecretsManagerClient()

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_SECRETS_MANAGER_SECRET_ID", "project-x/development/backend")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://placeholder:placeholder@localhost:5432/app"
    )
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=fake_client))

    settings = get_settings()

    assert settings.environment == "development"
    assert settings.database_url == "postgresql+asyncpg://secret-user:secret-pass@db:5432/app"
    assert settings.jwt_secret_key == TEST_SECRET
    assert settings.local_otp == "654321"
    assert os.environ["DATABASE_URL"] == settings.database_url
    assert captured == {
        "service_name": "secretsmanager",
        "kwargs": {"region_name": "ap-south-1"},
        "secret_id": "project-x/development/backend",
    }
