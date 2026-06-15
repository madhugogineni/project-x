import re
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from core.security import normalize_email, normalize_name, normalize_phone

ALLOWED_NOMINEE_RELATIONSHIPS = {
    "SPOUSE",
    "MOTHER",
    "FATHER",
    "SON",
    "DAUGHTER",
    "BROTHER",
    "SISTER",
    "OTHER",
}
RELATIONSHIP_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9 .&'/-]*$")
ALLOWED_SCOPE_PERMISSIONS = {
    "VIEW_SUMMARY",
    "VIEW_FULL",
    "VIEW_WITH_DOCUMENTS",
}
EDITABLE_NOMINEE_STATUSES = {"PENDING", "INVITED"}


class LinkedAccountResponse(BaseModel):
    id: str
    full_name: str | None
    phone: str
    email: str


class NomineeResponse(BaseModel):
    id: str
    full_name: str
    relationship: str
    phone: str | None
    email: str | None
    share_percentage: float | None
    status: str
    linked_account_id: str | None
    linked_at: datetime | None
    linked_account: LinkedAccountResponse | None = None
    created_at: datetime
    updated_at: datetime


class NomineeCreateRequest(BaseModel):
    full_name: str
    relationship: str
    phone: str
    email: str
    share_percentage: float | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return normalize_name(value, field_name="Full name")

    @field_validator("relationship")
    @classmethod
    def validate_relationship(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Relationship is required.")
        if len(normalized) > 50:
            raise ValueError("Relationship must be 50 characters or fewer.")
        if normalized not in ALLOWED_NOMINEE_RELATIONSHIPS and not RELATIONSHIP_PATTERN.fullmatch(
            normalized
        ):
            raise ValueError(
                "Relationship can contain only letters, numbers, spaces, and basic punctuation."
            )
        return normalized

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("share_percentage")
    @classmethod
    def validate_share_percentage(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("Share percentage must be between 0 and 100.")
        return value

    @model_validator(mode="after")
    def validate_contact_channels(self) -> "NomineeCreateRequest":
        if not self.phone or not self.email:
            raise ValueError("Phone number and email are required.")
        return self


class NomineeUpdateRequest(BaseModel):
    full_name: str | None = None
    relationship: str | None = None
    phone: str | None = None
    email: str | None = None
    share_percentage: float | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_name(value, field_name="Full name")

    @field_validator("relationship")
    @classmethod
    def validate_relationship(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Relationship is required.")
        if len(normalized) > 50:
            raise ValueError("Relationship must be 50 characters or fewer.")
        if normalized not in ALLOWED_NOMINEE_RELATIONSHIPS and not RELATIONSHIP_PATTERN.fullmatch(
            normalized
        ):
            raise ValueError(
                "Relationship can contain only letters, numbers, spaces, and basic punctuation."
            )
        return normalized

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_phone(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_email(value)

    @field_validator("share_percentage")
    @classmethod
    def validate_share_percentage(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0 or value > 100:
            raise ValueError("Share percentage must be between 0 and 100.")
        return value

    @model_validator(mode="after")
    def validate_has_updates(self) -> "NomineeUpdateRequest":
        if all(
            value is None
            for value in (
                self.full_name,
                self.relationship,
                self.phone,
                self.email,
                self.share_percentage,
            )
        ):
            raise ValueError("At least one nominee field must be provided.")
        if self.phone is None and self.email is None:
            return self
        if self.phone == "" and self.email == "":
            raise ValueError("At least one of phone or email is required.")
        return self


class NomineeScopeAssignmentInput(BaseModel):
    container_id: str
    permission: str

    @field_validator("container_id")
    @classmethod
    def validate_container_id(cls, value: str) -> str:
        container_id = value.strip()
        if not container_id:
            raise ValueError("Container id is required.")
        return container_id

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in ALLOWED_SCOPE_PERMISSIONS:
            raise ValueError(
                f"Permission must be one of: {', '.join(sorted(ALLOWED_SCOPE_PERMISSIONS))}."
            )
        return normalized


class NomineeScopeReplaceRequest(BaseModel):
    scopes: list[NomineeScopeAssignmentInput]

    @model_validator(mode="after")
    def validate_unique_containers(self) -> "NomineeScopeReplaceRequest":
        container_ids = [scope.container_id for scope in self.scopes]
        if len(container_ids) != len(set(container_ids)):
            raise ValueError("Each container may only appear once in scope.")
        return self


class NomineeVisibilityUpdateRequest(BaseModel):
    is_visible: bool
    all_assigned: bool = False
    container_ids: list[str] | None = None

    @field_validator("container_ids")
    @classmethod
    def validate_container_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = []
        for container_id in value:
            cleaned = container_id.strip()
            if not cleaned:
                raise ValueError("Container id is required.")
            normalized.append(cleaned)
        if len(normalized) != len(set(normalized)):
            raise ValueError("Each container may only appear once in visibility updates.")
        return normalized

    @model_validator(mode="after")
    def validate_selection_mode(self) -> "NomineeVisibilityUpdateRequest":
        has_container_ids = bool(self.container_ids)
        if self.all_assigned == has_container_ids:
            raise ValueError("Specify either all_assigned=true or a non-empty container_ids list.")
        return self


class NomineeScopeResponse(BaseModel):
    id: str
    container_id: str
    container_type: str
    institution_name: str
    permission: str
    is_active: bool
    is_visible: bool
    visibility_triggered_at: datetime | None
    visibility_trigger_source: str | None
    created_at: datetime
    updated_at: datetime
