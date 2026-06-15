from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from db.models.profile import ProfileType


class ProfileTypeCatalog(BaseModel):
    supported_types: list[str]


class ProfileCreateRequest(BaseModel):
    profile_type: str

    @field_validator("profile_type")
    @classmethod
    def validate_profile_type(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {profile_type.value for profile_type in ProfileType}:
            raise ValueError("Unsupported profile type.")
        return normalized


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    profile_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfileUpsertResponse(BaseModel):
    profile: ProfileResponse
    created: bool


class ProfileAccessRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    accessor_profile_id: str
    primary_profile_id: str
    status: str
    granted_at: datetime
    revoked_at: datetime | None
    revoke_reason: str | None


class ProfileAccessUpsertResult(BaseModel):
    access: ProfileAccessRecord
    created: bool
