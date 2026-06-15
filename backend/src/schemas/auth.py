from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from core.auth_configs import is_supported_otp_flow
from core.security import (
    normalize_email,
    normalize_name,
    normalize_phone,
    validate_pan_number,
)
from core.settings import get_settings

ALLOWED_GENDERS = {"MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"}


class OtpRequest(BaseModel):
    phone: str
    flow: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("flow")
    @classmethod
    def validate_flow(cls, value: str) -> str:
        flow = value.strip().upper()
        if not is_supported_otp_flow(flow):
            raise ValueError("Unsupported OTP flow.")
        return flow


class OtpSessionResponse(BaseModel):
    otp_session_id: str
    expires_at: datetime
    flow: str
    resend_count: int
    remaining_resends: int
    attempts_remaining: int
    cooldown_until: datetime | None = None


class OtpVerifyRequest(BaseModel):
    otp_session_id: str
    phone: str
    otp: str
    flow: str

    @field_validator("otp_session_id")
    @classmethod
    def validate_otp_session_id(cls, value: str) -> str:
        session_id = value.strip()
        if not session_id:
            raise ValueError("OTP session id is required.")
        return session_id

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        otp = value.strip()
        if not otp.isdigit():
            raise ValueError("OTP must contain digits only.")
        otp_length = get_settings().otp_length
        if len(otp) != otp_length:
            raise ValueError(f"OTP must be exactly {otp_length} digits long.")
        return otp

    @field_validator("flow")
    @classmethod
    def validate_flow(cls, value: str) -> str:
        flow = value.strip().upper()
        if not is_supported_otp_flow(flow):
            raise ValueError("Unsupported OTP flow.")
        return flow


class SignupVerificationResponse(BaseModel):
    verified_signup_token: str
    expires_at: datetime


class AddressInput(BaseModel):
    address_line_1: str
    address_line_2: str | None = None
    landmark: str | None = None
    city: str
    district: str | None = None
    state: str
    pincode: str
    country: str = "India"

    @field_validator(
        "address_line_1",
        "city",
        "state",
        "country",
        mode="before",
    )
    @classmethod
    def normalize_required_fields(cls, value: str) -> str:
        return normalize_name(value, field_name="Address field")

    @field_validator("address_line_2", "landmark", "district", mode="before")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) != 6:
            raise ValueError("Pincode must contain exactly 6 digits.")
        return digits


class SignupCompleteRequest(BaseModel):
    verified_signup_token: str
    email: str
    full_name: str
    date_of_birth: date
    gender: str
    pan_number: str
    name_on_pan: str
    current_address: AddressInput
    permanent_address: AddressInput | None = None
    is_same_as_current: bool = False

    @field_validator("verified_signup_token")
    @classmethod
    def validate_verified_signup_token(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("Verified signup token is required.")
        return token

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return normalize_name(value, field_name="Full name")

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Date of birth must be in the past.")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALLOWED_GENDERS:
            raise ValueError(f"Gender must be one of: {', '.join(sorted(ALLOWED_GENDERS))}.")
        return normalized

    @field_validator("pan_number")
    @classmethod
    def validate_pan_number(cls, value: str) -> str:
        return validate_pan_number(value)

    @field_validator("name_on_pan")
    @classmethod
    def validate_name_on_pan(cls, value: str) -> str:
        return normalize_name(value, field_name="Name on PAN")

    @model_validator(mode="after")
    def validate_permanent_address(self) -> "SignupCompleteRequest":
        if not self.is_same_as_current and self.permanent_address is None:
            raise ValueError("Permanent address is required when it differs from current address.")
        return self


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("Refresh token is required.")
        return token


class LogoutRequest(BaseModel):
    refresh_token: str | None = None

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip()
        if not token:
            raise ValueError("Refresh token cannot be blank.")
        return token


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    phone: str
    full_name: str | None
    email_verified: bool
    phone_verified: bool
    status: str
    primary_profile_id: str | None = None


class AuthTokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    account: AccountResponse


class LogoutResponse(BaseModel):
    revoked_access_token: bool
    revoked_refresh_token: bool


class AuthSessionResponse(BaseModel):
    id: str
    session_id: str
    jti: str
    token_type: str
    device_name: str | None
    ip_address: str | None
    user_agent: str | None
    revoked_at: datetime | None
    last_used_at: datetime
    created_at: datetime
    active_profile_id: str | None = None
