import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
PASSWORD_MIN_LENGTH = 12
FIELD_ENCRYPTION_VERSION = "v1"
FIELD_ENCRYPTION_NONCE_BYTES = 16
FIELD_ENCRYPTION_TAG_BYTES = 32


class TokenValidationError(ValueError):
    """Raised when a JWT cannot be verified or is no longer valid."""


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    jti: str
    token_type: str
    issued_at: datetime
    expires_at: datetime
    issuer: str
    audience: str
    profile_id: str | None = None
    extra_claims: dict[str, Any] = field(default_factory=dict)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value.strip())
    if not 10 <= len(digits) <= 15:
        raise ValueError("Phone number must contain between 10 and 15 digits.")
    return digits


def validate_password_strength(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")
    checks = [
        (re.search(r"[a-z]", value), "one lowercase letter"),
        (re.search(r"[A-Z]", value), "one uppercase letter"),
        (re.search(r"\d", value), "one number"),
        (re.search(r"[^A-Za-z0-9]", value), "one special character"),
    ]
    missing = [label for matched, label in checks if not matched]
    if missing:
        raise ValueError(f"Password must include at least {', '.join(missing)}.")
    return value


def validate_pan_number(value: str) -> str:
    normalized = value.strip().upper()
    if not PAN_PATTERN.match(normalized):
        raise ValueError("PAN must be in the format AAAAA9999A.")
    return normalized


def normalize_name(value: str, *, field_name: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) < 2:
        raise ValueError(f"{field_name} must be at least 2 characters long.")
    return normalized


def generate_numeric_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_secret(value: str) -> str:
    return hash_password(value)


def verify_secret(value: str, encoded_value: str) -> bool:
    return verify_password(value, encoded_value)


def encrypt_sensitive_value(value: str, secret_key: str) -> str:
    nonce = secrets.token_bytes(FIELD_ENCRYPTION_NONCE_BYTES)
    plaintext = value.encode("utf-8")
    secret_key_bytes = secret_key.encode("utf-8")
    ciphertext = _xor_with_keystream(plaintext, secret_key_bytes, nonce)
    tag = hmac.new(secret_key_bytes, nonce + ciphertext, hashlib.sha256).digest()
    payload = nonce + ciphertext + tag
    return f"{FIELD_ENCRYPTION_VERSION}.{_encode_b64url(payload)}"


def decrypt_sensitive_value(value: str, secret_key: str) -> str:
    try:
        version, encoded_payload = value.split(".", maxsplit=1)
    except ValueError as exc:
        raise ValueError("Encrypted value is malformed.") from exc

    if version != FIELD_ENCRYPTION_VERSION:
        raise ValueError("Encrypted value version is unsupported.")

    payload = _decode_b64url(encoded_payload)
    if len(payload) < FIELD_ENCRYPTION_NONCE_BYTES + FIELD_ENCRYPTION_TAG_BYTES:
        raise ValueError("Encrypted value payload is invalid.")

    nonce = payload[:FIELD_ENCRYPTION_NONCE_BYTES]
    tag = payload[-FIELD_ENCRYPTION_TAG_BYTES:]
    ciphertext = payload[FIELD_ENCRYPTION_NONCE_BYTES:-FIELD_ENCRYPTION_TAG_BYTES]
    secret_key_bytes = secret_key.encode("utf-8")
    expected_tag = hmac.new(secret_key_bytes, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, tag):
        raise ValueError("Encrypted value integrity check failed.")

    plaintext = _xor_with_keystream(ciphertext, secret_key_bytes, nonce)
    return plaintext.decode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_encode_b64url(salt)}${_encode_b64url(derived)}"
    )


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, n_value, r_value, p_value, salt, expected_hash = encoded_password.split("$")
    except ValueError:
        return False

    if algorithm != "scrypt":
        return False

    try:
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode_b64url(salt),
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
            dklen=SCRYPT_DKLEN,
        )
    except (ValueError, TypeError, binascii.Error):
        return False

    return hmac.compare_digest(_encode_b64url(derived), expected_hash)


def create_jwt(
    *,
    subject: str,
    token_type: str,
    secret_key: str,
    issuer: str,
    audience: str,
    expires_delta: timedelta,
    additional_claims: dict[str, Any] | None = None,
) -> tuple[str, TokenClaims]:
    issued_at = utc_now()
    expires_at = issued_at + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": str(uuid4()),
        "type": token_type,
        "iss": issuer,
        "aud": audience,
        "iat": int(issued_at.timestamp()),
        "nbf": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if additional_claims:
        payload.update(additional_claims)

    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _encode_b64url(
                json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
            ),
            _encode_b64url(
                json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            ),
        ]
    )
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    token = f"{signing_input}.{_encode_b64url(signature)}"

    return token, TokenClaims(
        subject=subject,
        jti=payload["jti"],
        token_type=token_type,
        issued_at=issued_at,
        expires_at=expires_at,
        issuer=issuer,
        audience=audience,
        profile_id=payload.get("profile_id"),
        extra_claims=_extract_extra_claims(payload),
    )


def decode_jwt(
    token: str,
    *,
    secret_key: str,
    issuer: str,
    audience: str,
    expected_token_type: str | None = None,
) -> TokenClaims:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise TokenValidationError("Malformed token.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    try:
        actual_signature = _decode_b64url(encoded_signature)
    except binascii.Error as exc:
        raise TokenValidationError("Malformed token signature.") from exc

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise TokenValidationError("Invalid token signature.")

    try:
        header = json.loads(_decode_b64url(encoded_header))
        payload = json.loads(_decode_b64url(encoded_payload))
    except (json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as exc:
        raise TokenValidationError("Malformed token payload.") from exc

    if header.get("alg") != "HS256":
        raise TokenValidationError("Unsupported token algorithm.")

    if payload.get("iss") != issuer or payload.get("aud") != audience:
        raise TokenValidationError("Token issuer or audience is invalid.")

    token_type = payload.get("type")
    if expected_token_type and token_type != expected_token_type:
        raise TokenValidationError("Token type is invalid for this operation.")

    subject = payload.get("sub")
    jti = payload.get("jti")
    if not subject or not jti:
        raise TokenValidationError("Token is missing required claims.")

    issued_at = _timestamp_to_datetime(payload.get("iat"), "iat")
    not_before = _timestamp_to_datetime(payload.get("nbf"), "nbf")
    expires_at = _timestamp_to_datetime(payload.get("exp"), "exp")
    now = utc_now()

    if now < not_before:
        raise TokenValidationError("Token is not active yet.")
    if now >= expires_at:
        raise TokenValidationError("Token has expired.")

    return TokenClaims(
        subject=subject,
        jti=jti,
        token_type=token_type,
        issued_at=issued_at,
        expires_at=expires_at,
        issuer=issuer,
        audience=audience,
        profile_id=payload.get("profile_id"),
        extra_claims=_extract_extra_claims(payload),
    )


def _timestamp_to_datetime(value: Any, claim_name: str) -> datetime:
    if not isinstance(value, int):
        raise TokenValidationError(f"Token claim '{claim_name}' is invalid.")
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _encode_b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _decode_b64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode())


def _xor_with_keystream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(data):
        keystream.extend(hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(left ^ right for left, right in zip(data, keystream[: len(data)], strict=False))


def _extract_extra_claims(payload: Mapping[str, Any]) -> dict[str, Any]:
    reserved_keys = {"sub", "jti", "type", "iss", "aud", "iat", "nbf", "exp", "profile_id"}
    return {key: value for key, value in payload.items() if key not in reserved_keys}
