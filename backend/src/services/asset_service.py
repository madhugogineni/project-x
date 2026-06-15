from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.security import decrypt_sensitive_value, encrypt_sensitive_value, normalize_email, utc_now
from core.settings import get_settings
from db.models import (
    AccountNominee,
    AccountNomineeScope,
    Asset,
    AssetBankDetail,
    AssetBusinessDetail,
    AssetCryptoDetail,
    AssetDematDetail,
    AssetDocument,
    AssetGovtSavingsDetail,
    AssetInsuranceDetail,
    AssetLoanDetail,
    AssetMutualFundDetail,
    AssetRealEstateDetail,
    AssetReceivableDetail,
    AssetRetirementDetail,
)
from schemas.asset import (
    AssetBlueprintResponse,
    AssetCreateRequest,
    AssetFieldBlueprint,
    AssetListItemResponse,
    AssetResponse,
    AssetTypeBlueprint,
    AssetTypeCatalogEntry,
    AssetTypeCatalogResponse,
    AssetUpdateRequest,
    DocumentDownloadUrlResponse,
    DocumentMetadataResponse,
    DocumentUploadCompleteRequest,
    DocumentUploadInitiateRequest,
    DocumentUploadInitiateResponse,
)
from schemas.pagination import PaginatedResponse, build_paginated_response
from services.auth_service import AuthenticatedAccountContext
from services.document_storage import get_document_storage_service
from services.resource_access_service import (
    NOMINEE_PERMISSION_FULL,
    NOMINEE_PERMISSION_WITH_DOCUMENTS,
    ResolvedResourceContext,
    resolve_resource_context,
)

DOCUMENT_STATUS_PENDING = "PENDING_UPLOAD"
DOCUMENT_STATUS_UPLOADED = "UPLOADED"
DOCUMENT_STATUS_FAILED = "FAILED"

DOCUMENT_TYPE_OPTIONS = (
    "POLICY_DOCUMENT",
    "PROPERTY_PAPER",
    "INVESTMENT_STATEMENT",
    "LEGAL_AGREEMENT",
    "ACCOUNT_STATEMENT",
    "OTHER",
)

INDIAN_STATE_OPTIONS = (
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
)


@dataclass(frozen=True)
class AssetFieldDefinition:
    api_name: str
    field_type: str
    model_attr: str | None = None
    encrypted_attr: str | None = None
    masked_attr: str | None = None
    required: bool = False
    enum_options: tuple[str, ...] = ()

    @property
    def sensitive(self) -> bool:
        return self.encrypted_attr is not None and self.masked_attr is not None

    @property
    def read_attr(self) -> str:
        if self.sensitive and self.masked_attr is not None:
            return self.masked_attr
        if self.model_attr is None:
            raise RuntimeError(f"Field {self.api_name} is misconfigured.")
        return self.model_attr


@dataclass(frozen=True)
class AssetTypeDefinition:
    container_type: str
    detail_model: type[Any]
    relationship_name: str
    fields: tuple[AssetFieldDefinition, ...]
    summary_fields: tuple[str, ...]

    def blueprint(self) -> AssetTypeBlueprint:
        return AssetTypeBlueprint(
            container_type=self.container_type,
            base_fields=list(BASE_BLUEPRINT_FIELDS),
            detail_fields=[
                AssetFieldBlueprint(
                    name=field.api_name,
                    type=field.field_type,
                    required=field.required,
                    enum_options=list(field.enum_options) if field.enum_options else None,
                    sensitive=field.sensitive,
                    masked_on_read=field.sensitive,
                )
                for field in self.fields
            ],
            document_support=True,
        )

    def catalog_entry(self) -> AssetTypeCatalogEntry:
        enum_fields = {
            field.api_name: list(field.enum_options) for field in self.fields if field.enum_options
        }
        return AssetTypeCatalogEntry(
            container_type=self.container_type,
            enum_fields=enum_fields,
        )


BASE_BLUEPRINT_FIELDS = (
    AssetFieldBlueprint(name="institution_name", type="string", required=True),
    AssetFieldBlueprint(name="approximate_value", type="decimal"),
    AssetFieldBlueprint(name="notes", type="string"),
)


def _field(
    name: str,
    field_type: str,
    *,
    required: bool = False,
    enum_options: tuple[str, ...] = (),
) -> AssetFieldDefinition:
    return AssetFieldDefinition(
        api_name=name,
        field_type=field_type,
        model_attr=name,
        required=required,
        enum_options=enum_options,
    )


def _sensitive_field(
    name: str,
    *,
    field_type: str = "string",
) -> AssetFieldDefinition:
    return AssetFieldDefinition(
        api_name=name,
        field_type=field_type,
        encrypted_attr=f"{name}_encrypted",
        masked_attr=f"{name}_masked",
    )


ASSET_TYPE_DEFINITIONS = {
    "BANK_RELATIONSHIP": AssetTypeDefinition(
        container_type="BANK_RELATIONSHIP",
        detail_model=AssetBankDetail,
        relationship_name="bank_detail",
        fields=(
            _sensitive_field("account_number"),
            _field(
                "account_type",
                "string",
                enum_options=("SAVINGS", "CURRENT", "FD", "RD", "LOCKER", "FOREIGN"),
            ),
            _field("ifsc_code", "string"),
            _field("branch_name", "string"),
            _field("city", "string"),
            _field("state", "string", enum_options=INDIAN_STATE_OPTIONS),
            _field("maturity_date", "date"),
            _field("interest_rate", "decimal"),
        ),
        summary_fields=("account_type", "account_number", "branch_name", "city", "state"),
    ),
    "DEMAT_ACCOUNT": AssetTypeDefinition(
        container_type="DEMAT_ACCOUNT",
        detail_model=AssetDematDetail,
        relationship_name="demat_detail",
        fields=(
            _field("dp_id", "string"),
            _sensitive_field("client_id"),
            _field("depository", "string", enum_options=("NSDL", "CDSL")),
            _field("broker_name", "string"),
        ),
        summary_fields=("dp_id", "client_id", "depository", "broker_name"),
    ),
    "MUTUAL_FUND_FOLIO": AssetTypeDefinition(
        container_type="MUTUAL_FUND_FOLIO",
        detail_model=AssetMutualFundDetail,
        relationship_name="mutual_fund_detail",
        fields=(
            _sensitive_field("folio_number"),
            _field("amc_name", "string"),
            _field("rta_name", "string", enum_options=("CAMS", "KFINTECH")),
        ),
        summary_fields=("amc_name", "folio_number", "rta_name"),
    ),
    "RETIREMENT_ACCOUNT": AssetTypeDefinition(
        container_type="RETIREMENT_ACCOUNT",
        detail_model=AssetRetirementDetail,
        relationship_name="retirement_detail",
        fields=(
            _field(
                "account_type",
                "string",
                enum_options=("EPF", "PPF", "NPS", "SUPERANNUATION", "PENSION"),
            ),
            _sensitive_field("reference_number"),
            _field("employer_name", "string"),
            _field("fund_manager", "string"),
        ),
        summary_fields=("account_type", "reference_number", "employer_name"),
    ),
    "INSURANCE_POLICY": AssetTypeDefinition(
        container_type="INSURANCE_POLICY",
        detail_model=AssetInsuranceDetail,
        relationship_name="insurance_detail",
        fields=(
            _sensitive_field("policy_number"),
            _field(
                "policy_type",
                "string",
                enum_options=("LIFE", "HEALTH", "ACCIDENT", "PROPERTY"),
            ),
            _field("sum_assured", "decimal"),
            _field("premium_amount", "decimal"),
            _field(
                "premium_frequency",
                "string",
                enum_options=("MONTHLY", "QUARTERLY", "ANNUAL", "SINGLE"),
            ),
            _field("policy_start_date", "date"),
            _field("maturity_date", "date"),
            _field("is_active_policy", "boolean"),
        ),
        summary_fields=("policy_type", "policy_number", "sum_assured", "maturity_date"),
    ),
    "REAL_ESTATE": AssetTypeDefinition(
        container_type="REAL_ESTATE",
        detail_model=AssetRealEstateDetail,
        relationship_name="real_estate_detail",
        fields=(
            _field(
                "property_type",
                "string",
                enum_options=("RESIDENTIAL", "COMMERCIAL", "LAND", "AGRICULTURAL"),
            ),
            _field("address", "string"),
            _field("city", "string"),
            _field("state", "string"),
            _field("pincode", "string"),
            _sensitive_field("registration_number"),
            _field("co_owner_name", "string"),
            _field("ownership_percentage", "decimal"),
        ),
        summary_fields=("property_type", "city", "state", "ownership_percentage"),
    ),
    "LOAN_ACCOUNT": AssetTypeDefinition(
        container_type="LOAN_ACCOUNT",
        detail_model=AssetLoanDetail,
        relationship_name="loan_detail",
        fields=(
            _field(
                "loan_type",
                "string",
                enum_options=("HOME", "PERSONAL", "BUSINESS", "GOLD", "VEHICLE", "GUARANTEE"),
            ),
            _sensitive_field("loan_account"),
            _field("outstanding_amount", "decimal"),
            _field("emi_amount", "decimal"),
            _field("emi_frequency", "string", enum_options=("MONTHLY", "QUARTERLY")),
            _field("loan_start_date", "date"),
            _field("loan_end_date", "date"),
        ),
        summary_fields=("loan_type", "loan_account", "outstanding_amount", "loan_end_date"),
    ),
    "BUSINESS_OWNERSHIP": AssetTypeDefinition(
        container_type="BUSINESS_OWNERSHIP",
        detail_model=AssetBusinessDetail,
        relationship_name="business_detail",
        fields=(
            _field(
                "business_type",
                "string",
                enum_options=("PRIVATE_LIMITED", "LLP", "PARTNERSHIP", "PROPRIETORSHIP"),
            ),
            _field("business_name", "string"),
            _field("ownership_percentage", "decimal"),
            _sensitive_field("cin"),
            _field("registered_address", "string"),
        ),
        summary_fields=("business_type", "business_name", "ownership_percentage"),
    ),
    "GOVERNMENT_SAVINGS_SCHEME": AssetTypeDefinition(
        container_type="GOVERNMENT_SAVINGS_SCHEME",
        detail_model=AssetGovtSavingsDetail,
        relationship_name="govt_savings_detail",
        fields=(
            _field(
                "scheme_type",
                "string",
                enum_options=(
                    "NSC",
                    "SSY",
                    "SCSS",
                    "POST_OFFICE_FD",
                    "POST_OFFICE_RD",
                    "KVP",
                    "OTHER",
                ),
            ),
            _sensitive_field("account_number"),
            _field("post_office_branch", "string"),
            _field("maturity_date", "date"),
            _field("interest_rate", "decimal"),
        ),
        summary_fields=("scheme_type", "account_number", "post_office_branch", "maturity_date"),
    ),
    "CRYPTO_ACCOUNT": AssetTypeDefinition(
        container_type="CRYPTO_ACCOUNT",
        detail_model=AssetCryptoDetail,
        relationship_name="crypto_detail",
        fields=(
            _field("custody_type", "string", enum_options=("EXCHANGE", "SELF_CUSTODY")),
            _field("exchange_name", "string"),
            _sensitive_field("registered_email", field_type="email"),
            _field("wallet_address", "string"),
        ),
        summary_fields=("custody_type", "exchange_name", "registered_email", "wallet_address"),
    ),
    "RECEIVABLE_CLAIM": AssetTypeDefinition(
        container_type="RECEIVABLE_CLAIM",
        detail_model=AssetReceivableDetail,
        relationship_name="receivable_detail",
        fields=(
            _field(
                "receivable_type",
                "string",
                enum_options=("EMPLOYER_DUES", "LEGAL_SETTLEMENT", "EARNOUT", "DEPOSIT", "OTHER"),
            ),
            _field("counterparty_name", "string"),
            _field("counterparty_contact", "string"),
            _field("expected_amount", "decimal"),
            _field("due_date", "date"),
            _field("description", "string"),
        ),
        summary_fields=("receivable_type", "counterparty_name", "expected_amount", "due_date"),
    ),
}

ASSET_LOAD_OPTIONS = (
    selectinload(Asset.bank_detail),
    selectinload(Asset.demat_detail),
    selectinload(Asset.mutual_fund_detail),
    selectinload(Asset.retirement_detail),
    selectinload(Asset.insurance_detail),
    selectinload(Asset.real_estate_detail),
    selectinload(Asset.loan_detail),
    selectinload(Asset.business_detail),
    selectinload(Asset.govt_savings_detail),
    selectinload(Asset.crypto_detail),
    selectinload(Asset.receivable_detail),
    selectinload(Asset.documents),
)


def get_asset_types() -> AssetTypeCatalogResponse:
    definitions = list(ASSET_TYPE_DEFINITIONS.values())
    return AssetTypeCatalogResponse(
        supported_types=[definition.container_type for definition in definitions],
        types=[definition.catalog_entry() for definition in definitions],
    )


def get_asset_blueprint() -> AssetBlueprintResponse:
    return AssetBlueprintResponse(
        types=[definition.blueprint() for definition in ASSET_TYPE_DEFINITIONS.values()]
    )


async def list_assets(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    profile_id: str,
    primary_profile_id: str | None,
    container_type: str | None = None,
    is_active: bool | None = True,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> PaginatedResponse[AssetListItemResponse]:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=False,
    )

    normalized_type = container_type.strip().upper() if container_type is not None else None
    if normalized_type is not None and normalized_type not in ASSET_TYPE_DEFINITIONS:
        raise _bad_request_error("Unsupported asset type.")

    if access_context.is_nominee:
        base_statement = (
            select(Asset.id, AccountNomineeScope.permission)
            .join(
                AccountNomineeScope,
                and_(
                    AccountNomineeScope.container_id == Asset.id,
                    AccountNomineeScope.is_active.is_(True),
                    AccountNomineeScope.is_visible.is_(True),
                ),
            )
            .join(AccountNominee, AccountNominee.id == AccountNomineeScope.account_nominee_id)
            .where(
                AccountNominee.primary_account_id == access_context.primary_account_id,
                AccountNominee.nominee_profile_id == access_context.actor_profile.id,
                AccountNominee.status == "LINKED",
                Asset.account_id == access_context.primary_account_id,
            )
        )
        statement = (
            select(Asset, AccountNomineeScope.permission)
            .join(
                AccountNomineeScope,
                and_(
                    AccountNomineeScope.container_id == Asset.id,
                    AccountNomineeScope.is_active.is_(True),
                    AccountNomineeScope.is_visible.is_(True),
                ),
            )
            .join(AccountNominee, AccountNominee.id == AccountNomineeScope.account_nominee_id)
            .where(
                AccountNominee.primary_account_id == access_context.primary_account_id,
                AccountNominee.nominee_profile_id == access_context.actor_profile.id,
                AccountNominee.status == "LINKED",
                Asset.account_id == access_context.primary_account_id,
            )
            .options(*ASSET_LOAD_OPTIONS)
        )
    else:
        base_statement = select(Asset.id).where(
            Asset.account_id == access_context.primary_account_id
        )
        statement = (
            select(Asset)
            .where(Asset.account_id == access_context.primary_account_id)
            .options(*ASSET_LOAD_OPTIONS)
        )

    if normalized_type is not None:
        base_statement = base_statement.where(Asset.container_type == normalized_type)
        statement = statement.where(Asset.container_type == normalized_type)
    if is_active is not None:
        base_statement = base_statement.where(Asset.is_active.is_(is_active))
        statement = statement.where(Asset.is_active.is_(is_active))
    if search:
        term = f"%{search.strip()}%"
        base_statement = base_statement.where(
            or_(
                Asset.institution_name.ilike(term),
                Asset.notes.ilike(term),
            )
        )
        statement = statement.where(
            or_(
                Asset.institution_name.ilike(term),
                Asset.notes.ilike(term),
            )
        )

    total = await session.scalar(
        select(func.count()).select_from(base_statement.order_by(None).subquery())
    )

    if access_context.is_nominee:
        rows = (
            await session.execute(
                statement.order_by(Asset.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()
        items = [
            _build_asset_list_response(
                asset,
                access_context=access_context,
                access_permission=permission,
            )
            for asset, permission in rows
        ]
        return build_paginated_response(
            items=items,
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    assets = (
        await session.scalars(
            statement.order_by(Asset.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    items = [
        _build_asset_list_response(
            asset,
            access_context=access_context,
            access_permission=None,
        )
        for asset in assets
    ]
    return build_paginated_response(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


async def get_asset(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    asset_id: str,
    profile_id: str,
    primary_profile_id: str | None,
) -> AssetResponse:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=False,
    )

    asset, access_permission = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset_id,
        include_inactive=not access_context.is_nominee,
    )
    return _build_asset_response(
        asset,
        access_context=access_context,
        access_permission=access_permission,
    )


async def create_asset(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    payload: AssetCreateRequest,
) -> AssetResponse:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=payload.profile_id,
        primary_profile_id=payload.primary_profile_id,
        require_write=True,
    )
    definition = _get_asset_definition(payload.container_type)

    asset = Asset(
        account_id=access_context.primary_account_id,
        added_by_account_id=auth_context.account.id,
        container_type=definition.container_type,
        institution_name=payload.institution_name,
        nickname=payload.nickname,
        approximate_value=payload.approximate_value,
        notes=payload.notes,
        is_active=True,
    )
    session.add(asset)
    await session.flush()

    detail_record = definition.detail_model(container_id=asset.id)
    session.add(detail_record)
    _apply_detail_payload(definition, detail_record, payload.detail)
    await session.flush()
    asset, _ = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset.id,
        include_inactive=True,
    )

    return _build_asset_response(
        asset,
        access_context=access_context,
        access_permission=None,
    )


async def update_asset(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    asset_id: str,
    payload: AssetUpdateRequest,
) -> AssetResponse:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=payload.profile_id,
        primary_profile_id=payload.primary_profile_id,
        require_write=True,
    )
    asset, _ = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset_id,
        include_inactive=True,
        for_update=True,
    )
    definition = _get_asset_definition(asset.container_type)

    if payload.institution_name is not None:
        asset.institution_name = payload.institution_name
    if payload.nickname is not None:
        asset.nickname = payload.nickname
    if payload.approximate_value is not None:
        asset.approximate_value = payload.approximate_value
    if payload.notes is not None:
        asset.notes = payload.notes

    if payload.detail is not None:
        detail_record = getattr(asset, definition.relationship_name)
        if detail_record is None:
            detail_record = definition.detail_model(container_id=asset.id)
            session.add(detail_record)
        _apply_detail_payload(definition, detail_record, payload.detail)

    await session.flush()
    asset, _ = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset.id,
        include_inactive=True,
    )
    return _build_asset_response(
        asset,
        access_context=access_context,
        access_permission=None,
    )


async def delete_asset(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    asset_id: str,
    profile_id: str,
    primary_profile_id: str | None,
) -> AssetResponse:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=True,
    )
    asset, _ = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset_id,
        include_inactive=True,
        for_update=True,
    )
    asset.is_active = False
    await session.flush()
    return _build_asset_response(
        asset,
        access_context=access_context,
        access_permission=None,
    )


async def list_asset_documents(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    asset_id: str,
    profile_id: str,
    primary_profile_id: str | None,
    limit: int = 20,
    offset: int = 0,
) -> PaginatedResponse[DocumentMetadataResponse]:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=False,
    )
    asset, access_permission = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset_id,
        include_inactive=not access_context.is_nominee,
    )

    if access_context.is_nominee and access_permission != NOMINEE_PERMISSION_WITH_DOCUMENTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This nominee profile cannot access asset documents.",
        )

    visible_documents = _get_visible_documents(
        asset,
        access_context=access_context,
        access_permission=access_permission,
    )
    page_items = visible_documents[offset : offset + limit]
    items = [_build_document_response(document) for document in page_items]
    return build_paginated_response(
        items=items,
        total=len(visible_documents),
        limit=limit,
        offset=offset,
    )


async def initiate_document_upload(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    asset_id: str,
    payload: DocumentUploadInitiateRequest,
) -> DocumentUploadInitiateResponse:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=payload.profile_id,
        primary_profile_id=payload.primary_profile_id,
        require_write=True,
    )
    asset, _ = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset_id,
        include_inactive=True,
        for_update=True,
    )
    if payload.document_type not in DOCUMENT_TYPE_OPTIONS:
        raise _bad_request_error("Unsupported document type.")

    settings = get_settings()
    now = utc_now()
    document = AssetDocument(
        container_id=asset.id,
        account_id=asset.account_id,
        added_by_account_id=auth_context.account.id,
        document_type=payload.document_type,
        s3_key="",
        original_file_name_encrypted=encrypt_sensitive_value(
            payload.original_file_name,
            settings.active_field_encryption_key,
        ),
        file_name_hash=_hash_file_name(payload.original_file_name),
        file_size_bytes=payload.file_size_bytes,
        mime_type=payload.mime_type,
        upload_status=DOCUMENT_STATUS_PENDING,
        is_active=True,
        created_at=now,
    )
    session.add(document)
    await session.flush()

    object_key = f"documents/{asset.account_id}/{asset.id}/{document.id}"
    document.s3_key = object_key
    storage = get_document_storage_service()
    upload = storage.create_upload_url(
        object_key=object_key,
        mime_type=payload.mime_type,
    )
    await session.flush()

    return DocumentUploadInitiateResponse(
        document_id=document.id,
        upload_url=upload.url,
        upload_headers=upload.headers,
        expires_at=upload.expires_at,
    )


async def complete_document_upload(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    asset_id: str,
    document_id: str,
    payload: DocumentUploadCompleteRequest,
) -> DocumentMetadataResponse:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=payload.profile_id,
        primary_profile_id=payload.primary_profile_id,
        require_write=True,
    )
    asset, _ = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=asset_id,
        include_inactive=True,
    )
    document = await _get_document_for_update(session, document_id)
    if document.container_id != asset.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if get_document_storage_service().object_exists(object_key=document.s3_key):
        document.upload_status = DOCUMENT_STATUS_UPLOADED
    else:
        document.upload_status = DOCUMENT_STATUS_FAILED
        raise _bad_request_error("Uploaded document could not be verified.")

    await session.flush()
    return _build_document_response(document)


async def get_document_metadata(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    document_id: str,
    profile_id: str,
    primary_profile_id: str | None,
) -> DocumentMetadataResponse:
    document, _asset, _access_context = await _get_document_and_context(
        session,
        auth_context,
        document_id=document_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=False,
    )
    return _build_document_response(document)


async def get_document_download_url(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    document_id: str,
    profile_id: str,
    primary_profile_id: str | None,
) -> DocumentDownloadUrlResponse:
    document, _asset, _access_context = await _get_document_and_context(
        session,
        auth_context,
        document_id=document_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=False,
    )
    if document.upload_status != DOCUMENT_STATUS_UPLOADED:
        raise _bad_request_error("Only uploaded documents can be downloaded.")

    download = get_document_storage_service().create_download_url(object_key=document.s3_key)
    return DocumentDownloadUrlResponse(
        download_url=download.url,
        expires_at=download.expires_at,
    )


async def delete_document(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    document_id: str,
    profile_id: str,
    primary_profile_id: str | None,
) -> DocumentMetadataResponse:
    document, _asset, _access_context = await _get_document_and_context(
        session,
        auth_context,
        document_id=document_id,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=True,
    )
    document.is_active = False
    await session.flush()
    return _build_document_response(document)


async def _get_asset_for_context(
    session: AsyncSession,
    *,
    access_context: ResolvedResourceContext,
    asset_id: str,
    include_inactive: bool,
    for_update: bool = False,
) -> tuple[Asset, str | None]:
    if access_context.is_nominee:
        statement = (
            select(Asset, AccountNomineeScope.permission)
            .join(
                AccountNomineeScope,
                and_(
                    AccountNomineeScope.container_id == Asset.id,
                    AccountNomineeScope.is_active.is_(True),
                    AccountNomineeScope.is_visible.is_(True),
                ),
            )
            .join(AccountNominee, AccountNominee.id == AccountNomineeScope.account_nominee_id)
            .where(Asset.id == asset_id)
            .where(
                AccountNominee.primary_account_id == access_context.primary_account_id,
                AccountNominee.nominee_profile_id == access_context.actor_profile.id,
                AccountNominee.status == "LINKED",
                Asset.account_id == access_context.primary_account_id,
            )
            .options(*ASSET_LOAD_OPTIONS)
        )
        if not include_inactive:
            statement = statement.where(Asset.is_active.is_(True))
        if for_update:
            statement = statement.with_for_update()
        row = (await session.execute(statement)).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found.",
            )
        return row[0], row[1]

    statement = (
        select(Asset)
        .where(
            Asset.id == asset_id,
            Asset.account_id == access_context.primary_account_id,
        )
        .options(*ASSET_LOAD_OPTIONS)
    )
    if not include_inactive:
        statement = statement.where(Asset.is_active.is_(True))
    if for_update:
        statement = statement.with_for_update()
    asset = await session.scalar(statement)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        )
    return asset, None


async def _get_document_and_context(
    session: AsyncSession,
    auth_context: AuthenticatedAccountContext,
    *,
    document_id: str,
    profile_id: str,
    primary_profile_id: str | None,
    require_write: bool,
) -> tuple[AssetDocument, Asset, ResolvedResourceContext]:
    access_context = await resolve_resource_context(
        session,
        auth_context,
        profile_id=profile_id,
        primary_profile_id=primary_profile_id,
        require_write=require_write,
    )
    statement = select(AssetDocument).where(AssetDocument.id == document_id)
    if require_write:
        statement = statement.with_for_update()
    document = await session.scalar(statement)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    asset, access_permission = await _get_asset_for_context(
        session,
        access_context=access_context,
        asset_id=document.container_id,
        include_inactive=not access_context.is_nominee,
        for_update=require_write,
    )
    if document.container_id != asset.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    visible_documents = _get_visible_documents(
        asset,
        access_context=access_context,
        access_permission=access_permission,
    )
    if not any(existing.id == document.id for existing in visible_documents):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This profile cannot access the requested document.",
        )
    return document, asset, access_context


async def _get_document_for_update(session: AsyncSession, document_id: str) -> AssetDocument:
    document = await session.scalar(
        select(AssetDocument).where(AssetDocument.id == document_id).with_for_update()
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return document


def _build_asset_list_response(
    asset: Asset,
    *,
    access_context: ResolvedResourceContext,
    access_permission: str | None,
) -> AssetListItemResponse:
    definition = _get_asset_definition(asset.container_type)
    return AssetListItemResponse(
        id=asset.id,
        container_type=asset.container_type,
        institution_name=asset.institution_name,
        nickname=asset.nickname,
        approximate_value=asset.approximate_value,
        notes=asset.notes,
        is_active=asset.is_active,
        detail_summary=_serialize_detail_summary(asset, definition),
        document_count=len(
            _get_visible_documents(
                asset,
                access_context=access_context,
                access_permission=access_permission,
            )
        ),
        can_edit=access_context.can_write,
        can_delete=access_context.can_write,
        access_permission=access_permission,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _build_asset_response(
    asset: Asset,
    *,
    access_context: ResolvedResourceContext,
    access_permission: str | None,
) -> AssetResponse:
    definition = _get_asset_definition(asset.container_type)
    include_full_detail = not access_context.is_nominee or access_permission in {
        NOMINEE_PERMISSION_FULL,
        NOMINEE_PERMISSION_WITH_DOCUMENTS,
    }
    documents = [
        _build_document_response(document)
        for document in _get_visible_documents(
            asset,
            access_context=access_context,
            access_permission=access_permission,
        )
    ]
    list_item = _build_asset_list_response(
        asset,
        access_context=access_context,
        access_permission=access_permission,
    )
    return AssetResponse(
        **list_item.model_dump(),
        detail=_serialize_detail(asset, definition) if include_full_detail else None,
        documents=documents,
    )


def _build_document_response(document: AssetDocument) -> DocumentMetadataResponse:
    return DocumentMetadataResponse(
        id=document.id,
        container_id=document.container_id,
        document_type=document.document_type,
        original_file_name=_decrypt_original_file_name(document),
        mime_type=document.mime_type,
        file_size_bytes=document.file_size_bytes,
        upload_status=document.upload_status,
        is_active=document.is_active,
        created_at=document.created_at,
    )


def _serialize_detail(asset: Asset, definition: AssetTypeDefinition) -> dict[str, Any]:
    detail_record = getattr(asset, definition.relationship_name)
    if detail_record is None:
        return {}
    response: dict[str, Any] = {}
    for field in definition.fields:
        response[field.api_name] = getattr(detail_record, field.read_attr)
    return {key: value for key, value in response.items() if value is not None}


def _serialize_detail_summary(asset: Asset, definition: AssetTypeDefinition) -> dict[str, Any]:
    detail = _serialize_detail(asset, definition)
    return {
        field_name: detail[field_name]
        for field_name in definition.summary_fields
        if detail.get(field_name) is not None
    }


def _get_visible_documents(
    asset: Asset,
    *,
    access_context: ResolvedResourceContext,
    access_permission: str | None,
) -> list[AssetDocument]:
    documents = [document for document in asset.documents if document.is_active]
    if access_context.is_nominee:
        if access_permission != NOMINEE_PERMISSION_WITH_DOCUMENTS:
            return []
        return [
            document for document in documents if document.upload_status == DOCUMENT_STATUS_UPLOADED
        ]
    return documents


def _get_asset_definition(container_type: str) -> AssetTypeDefinition:
    normalized = container_type.strip().upper()
    definition = ASSET_TYPE_DEFINITIONS.get(normalized)
    if definition is None:
        raise _bad_request_error("Unsupported asset type.")
    return definition


def _apply_detail_payload(
    definition: AssetTypeDefinition,
    detail_record: Any,
    payload: dict[str, Any],
) -> None:
    unknown_fields = set(payload) - {field.api_name for field in definition.fields}
    if unknown_fields:
        unknown = ", ".join(sorted(unknown_fields))
        raise _bad_request_error(
            f"Unsupported detail fields for {definition.container_type}: {unknown}"
        )

    for field in definition.fields:
        if field.api_name not in payload:
            continue
        coerced_value = _coerce_value(field, payload[field.api_name])
        if field.sensitive:
            if coerced_value is None:
                setattr(detail_record, field.encrypted_attr, None)
                setattr(detail_record, field.masked_attr, None)
            else:
                setattr(
                    detail_record,
                    field.encrypted_attr,
                    encrypt_sensitive_value(
                        str(coerced_value),
                        get_settings().active_field_encryption_key,
                    ),
                )
                setattr(
                    detail_record,
                    field.masked_attr,
                    _mask_sensitive_value(str(coerced_value), field.api_name),
                )
            continue

        setattr(detail_record, field.model_attr, coerced_value)


def _coerce_value(field: AssetFieldDefinition, value: Any) -> Any:
    if value is None:
        return None

    if field.enum_options:
        if not isinstance(value, str):
            raise _bad_request_error(f"{field.api_name} must be a string.")
        stripped = value.strip()
        options_by_normalized_value = {option.upper(): option for option in field.enum_options}
        normalized = stripped.upper()
        canonical_value = options_by_normalized_value.get(normalized)
        if canonical_value is None:
            if "OTHER" in field.enum_options and stripped:
                return stripped
            raise _bad_request_error(
                f"{field.api_name} must be one of: {', '.join(field.enum_options)}."
            )
        return canonical_value

    if field.field_type in {"string", "email"}:
        if not isinstance(value, str):
            raise _bad_request_error(f"{field.api_name} must be a string.")
        normalized = value.strip()
        if field.api_name == "account_number" and normalized and not normalized.isdigit():
            raise _bad_request_error(f"{field.api_name} must contain only digits.")
        if field.field_type == "email":
            return normalize_email(normalized)
        return normalized

    if field.field_type == "decimal":
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise _bad_request_error(f"{field.api_name} must be a valid number.") from exc

    if field.field_type == "date":
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            raise _bad_request_error(f"{field.api_name} must be an ISO date string.")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise _bad_request_error(f"{field.api_name} must be an ISO date string.") from exc

    if field.field_type == "boolean":
        if not isinstance(value, bool):
            raise _bad_request_error(f"{field.api_name} must be true or false.")
        return value

    raise _bad_request_error(f"{field.api_name} uses an unsupported field type.")


def _mask_sensitive_value(value: str, field_name: str) -> str:
    if field_name == "registered_email":
        local, _, domain = value.partition("@")
        local_prefix = local[:2]
        return f"{local_prefix}{'*' * max(len(local) - len(local_prefix), 1)}@{domain}"

    trimmed = value.strip()
    if len(trimmed) <= 4:
        return "*" * len(trimmed)
    return f"{'X' * (len(trimmed) - 4)}{trimmed[-4:]}"


def _hash_file_name(original_file_name: str) -> str:
    return hashlib.sha256(original_file_name.encode("utf-8")).hexdigest()


def _decrypt_original_file_name(document: AssetDocument) -> str:
    return decrypt_sensitive_value(
        document.original_file_name_encrypted,
        get_settings().active_field_encryption_key,
    )


def _bad_request_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
