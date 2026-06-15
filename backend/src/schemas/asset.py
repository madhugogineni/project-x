from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ProfileScopedRequest(BaseModel):
    profile_id: str
    primary_profile_id: str | None = None

    @model_validator(mode="after")
    def normalize_profile_context(self) -> ProfileScopedRequest:
        self.profile_id = self.profile_id.strip()
        if self.primary_profile_id is not None:
            self.primary_profile_id = self.primary_profile_id.strip()
        return self


class AssetFieldBlueprint(BaseModel):
    name: str
    type: str
    required: bool = False
    enum_options: list[str] | None = None
    sensitive: bool = False
    masked_on_read: bool = False


class AssetTypeBlueprint(BaseModel):
    container_type: str
    base_fields: list[AssetFieldBlueprint]
    detail_fields: list[AssetFieldBlueprint]
    document_support: bool = True


class AssetBlueprintResponse(BaseModel):
    types: list[AssetTypeBlueprint]


class AssetTypeCatalogEntry(BaseModel):
    container_type: str
    enum_fields: dict[str, list[str]] = Field(default_factory=dict)


class AssetTypeCatalogResponse(BaseModel):
    supported_types: list[str]
    types: list[AssetTypeCatalogEntry]


class AssetCreateRequest(ProfileScopedRequest):
    container_type: str
    institution_name: str
    nickname: str | None = None
    approximate_value: Decimal | None = None
    notes: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_asset_create(self) -> AssetCreateRequest:
        self.container_type = self.container_type.strip().upper()
        self.institution_name = self.institution_name.strip()
        if not self.institution_name:
            raise ValueError("Institution name is required.")
        return self


class AssetUpdateRequest(ProfileScopedRequest):
    institution_name: str | None = None
    nickname: str | None = None
    approximate_value: Decimal | None = None
    notes: str | None = None
    detail: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> AssetUpdateRequest:
        if self.institution_name is not None:
            self.institution_name = self.institution_name.strip()
            if not self.institution_name:
                raise ValueError("Institution name cannot be empty.")

        if (
            self.institution_name is None
            and self.nickname is None
            and self.approximate_value is None
            and self.notes is None
            and self.detail is None
        ):
            raise ValueError("At least one asset field must be provided.")
        return self


class AssetDocumentSummaryResponse(BaseModel):
    id: str
    container_id: str
    document_type: str
    original_file_name: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    upload_status: str
    is_active: bool
    created_at: datetime


class AssetListItemResponse(BaseModel):
    id: str
    container_type: str
    institution_name: str
    nickname: str | None = None
    approximate_value: Decimal | None = None
    notes: str | None = None
    is_active: bool
    detail_summary: dict[str, Any] = Field(default_factory=dict)
    document_count: int
    can_edit: bool
    can_delete: bool
    access_permission: str | None = None
    created_at: datetime
    updated_at: datetime


class AssetResponse(AssetListItemResponse):
    detail: dict[str, Any] | None = None
    documents: list[AssetDocumentSummaryResponse] = Field(default_factory=list)


class DocumentUploadInitiateRequest(ProfileScopedRequest):
    document_type: str
    original_file_name: str
    mime_type: str | None = None
    file_size_bytes: int | None = None

    @model_validator(mode="after")
    def normalize_document_create(self) -> DocumentUploadInitiateRequest:
        self.document_type = self.document_type.strip().upper()
        self.original_file_name = self.original_file_name.strip()
        if not self.original_file_name:
            raise ValueError("Original file name is required.")
        return self


class DocumentUploadCompleteRequest(ProfileScopedRequest):
    document_id: str
    etag: str | None = None


class DocumentDownloadUrlRequest(ProfileScopedRequest):
    pass


class DocumentUploadInitiateResponse(BaseModel):
    document_id: str
    upload_url: str
    upload_headers: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime


class DocumentDownloadUrlResponse(BaseModel):
    download_url: str
    expires_at: datetime


class DocumentMetadataResponse(AssetDocumentSummaryResponse):
    pass


JsonScalar = str | int | float | bool | None | date | datetime | Decimal
