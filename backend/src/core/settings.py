from __future__ import annotations

import json
import os
from functools import lru_cache
from threading import Lock
from typing import Any, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRETS_MANAGER_ENVIRONMENTS = {"development", "production"}

_secrets_bootstrap_lock = Lock()
_secrets_bootstrapped = False


class BootstrapSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["local", "development", "staging", "production"] = "local"
    aws_region: str | None = None
    aws_secrets_manager_secret_id: str | None = None
    aws_secrets_manager_endpoint_url: str | None = None

    @property
    def should_load_aws_secrets(self) -> bool:
        return (
            self.environment in SECRETS_MANAGER_ENVIRONMENTS
            and self.aws_secrets_manager_secret_id is not None
        )


class Settings(BootstrapSettings):
    project_name: str = "Project X API"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    allowed_origins: str = "http://localhost:3020,http://localhost:3021"
    s3_bucket_name: str = "projectx-documents-local"
    s3_endpoint_url: str | None = None
    kms_key_id: str = "alias/projectx-local"
    jwt_secret_key: str = "change-this-local-dev-jwt-secret-before-production"
    field_encryption_key: str | None = None
    jwt_issuer: str = "project-x-api"
    jwt_audience: str = "project-x-clients"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    otp_ttl_minutes: int = 5
    verified_signup_ttl_minutes: int = 10
    otp_length: int = 6
    local_otp: str = "123456"
    document_presigned_url_ttl_seconds: int = 900
    inactivity_reminder_days: int = 30
    inactivity_escalation_days: int = 90
    inactivity_trigger_days: int = 120
    release_hold_days: int = 7

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long.")
        return value

    @field_validator("field_encryption_key")
    @classmethod
    def validate_field_encryption_key(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 32:
            raise ValueError("Field encryption key must be at least 32 characters long.")
        return value

    @field_validator("otp_length")
    @classmethod
    def validate_otp_length(cls, value: int) -> int:
        if not 4 <= value <= 8:
            raise ValueError("OTP length must be between 4 and 8 digits.")
        return value

    @field_validator("local_otp")
    @classmethod
    def validate_local_otp(cls, value: str) -> str:
        otp = value.strip()
        if not otp:
            raise ValueError("LOCAL_OTP is required.")
        if not otp.isdigit():
            raise ValueError("LOCAL_OTP must contain digits only.")
        return otp

    @model_validator(mode="after")
    def validate_local_otp_length(self) -> Settings:
        if len(self.local_otp) != self.otp_length:
            raise ValueError("LOCAL_OTP must match OTP_LENGTH.")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def active_field_encryption_key(self) -> str:
        return self.field_encryption_key or self.jwt_secret_key


def _stringify_secret_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _fetch_aws_secrets(bootstrap: BootstrapSettings) -> dict[str, str]:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required to load secrets from AWS Secrets Manager.") from exc

    client_kwargs: dict[str, str] = {}
    if bootstrap.aws_region:
        client_kwargs["region_name"] = bootstrap.aws_region
    if bootstrap.aws_secrets_manager_endpoint_url:
        client_kwargs["endpoint_url"] = bootstrap.aws_secrets_manager_endpoint_url

    client = boto3.client("secretsmanager", **client_kwargs)
    response = client.get_secret_value(SecretId=bootstrap.aws_secrets_manager_secret_id)
    secret_string = response.get("SecretString")
    if secret_string is None:
        raise RuntimeError("AWS Secrets Manager secret must provide SecretString JSON.")

    payload = json.loads(secret_string)
    if not isinstance(payload, dict):
        raise RuntimeError("AWS Secrets Manager secret must decode to a JSON object.")

    return {
        str(key): _stringify_secret_value(value)
        for key, value in payload.items()
        if value is not None
    }


def load_aws_secrets_into_environment() -> None:
    global _secrets_bootstrapped

    if _secrets_bootstrapped:
        return

    with _secrets_bootstrap_lock:
        if _secrets_bootstrapped:
            return

        bootstrap = BootstrapSettings()
        if bootstrap.should_load_aws_secrets:
            os.environ.update(_fetch_aws_secrets(bootstrap))

        _secrets_bootstrapped = True


@lru_cache
def get_settings() -> Settings:
    load_aws_secrets_into_environment()
    return Settings()


def reset_settings_cache() -> None:
    global _secrets_bootstrapped

    _secrets_bootstrapped = False
    get_settings.cache_clear()
