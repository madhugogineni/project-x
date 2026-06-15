from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.security import create_jwt, encrypt_sensitive_value
from db.models import (
    AccountNominee,
    AccountNomineeScope,
    Asset,
    AssetBankDetail,
    AssetBusinessDetail,
    AssetDocument,
    AssetInsuranceDetail,
    AssetLoanDetail,
    AssetRealEstateDetail,
    Profile,
    ProfileAccess,
    ProfileType,
)
from schemas.asset import AssetCreateRequest
from schemas.nominee import NomineeScopeReplaceRequest, NomineeVisibilityUpdateRequest
from services import asset_service, nominee_service, resource_access_service
from services.auth_service import AuthenticatedAccountContext

TEST_SECRET = "test-secret-key-which-is-definitely-long-enough"
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mock_access_data.json"
NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def _load_fixture() -> dict:
    with FIXTURE_PATH.open() as fixture_file:
        return json.load(fixture_file)


def _account_map(data: dict) -> dict[str, dict]:
    return {row["id"]: row for row in data["accounts"]}


def _profile_map(data: dict) -> dict[str, dict]:
    return {row["id"]: row for row in data["profiles"]}


def _profile_access_map(data: dict) -> dict[str, dict]:
    return {row["id"]: row for row in data["profile_access"]}


def _nominee_map(data: dict) -> dict[str, dict]:
    return {row["id"]: row for row in data["nominees"]}


def _asset_map(data: dict) -> dict[str, dict]:
    return {row["id"]: row for row in data["assets"]}


def _document_rows_by_asset(data: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in data["documents"]:
        grouped.setdefault(row["container_id"], []).append(row)
    return grouped


def _build_auth_context(
    data: dict,
    *,
    account_id: str,
    profile_id: str,
) -> AuthenticatedAccountContext:
    account_row = _account_map(data)[account_id]
    _, claims = create_jwt(
        subject=account_id,
        token_type="ACCESS",
        secret_key=TEST_SECRET,
        issuer="project-x-api",
        audience="project-x-clients",
        expires_delta=timedelta(minutes=5),
        additional_claims={"profile_id": profile_id, "session_id": "session-test-001"},
    )
    return AuthenticatedAccountContext(
        account=SimpleNamespace(**account_row),
        profile_id=profile_id,
        claims=claims,
        session_id="session-test-001",
    )


def _build_profile(data: dict, profile_id: str) -> Profile:
    row = _profile_map(data)[profile_id]
    profile = Profile(
        id=row["id"],
        account_id=row["account_id"],
        profile_type=ProfileType(row["profile_type"]),
        is_active=row["is_active"],
    )
    profile.created_at = NOW
    profile.updated_at = NOW
    return profile


def _build_profile_access(data: dict, access_id: str) -> ProfileAccess:
    row = _profile_access_map(data)[access_id]
    access = ProfileAccess(
        id=row["id"],
        accessor_profile_id=row["accessor_profile_id"],
        primary_profile_id=row["primary_profile_id"],
        status=row["status"],
        granted_at=NOW,
    )
    access.created_at = NOW
    access.updated_at = NOW
    return access


def _build_nominee(data: dict, nominee_id: str) -> AccountNominee:
    row = _nominee_map(data)[nominee_id]
    nominee = AccountNominee(
        id=row["id"],
        primary_account_id=row["primary_account_id"],
        added_by_account_id=row["added_by_account_id"],
        full_name=row["full_name"],
        nominee_relationship=row["relationship"],
        phone=row["phone"],
        email=row["email"],
        share_percentage=row["share_percentage"],
        status=row["status"],
        linked_account_id=row["linked_account_id"],
        nominee_profile_id=row["nominee_profile_id"],
    )
    nominee.created_at = NOW
    nominee.updated_at = NOW
    nominee.linked_at = NOW if nominee.linked_account_id else None
    return nominee


def _build_scope(data: dict, scope_id: str) -> AccountNomineeScope:
    row = next(item for item in data["nominee_scopes"] if item["id"] == scope_id)
    scope = AccountNomineeScope(
        id=row["id"],
        account_nominee_id=row["account_nominee_id"],
        added_by_account_id="acct-primary-001",
        container_id=row["container_id"],
        permission=row["permission"],
        is_active=row["is_active"],
        is_visible=row["is_visible"],
        visibility_trigger_source=row["visibility_trigger_source"],
    )
    scope.created_at = NOW
    scope.updated_at = NOW
    scope.visibility_triggered_at = NOW if row["visibility_trigger_source"] else None
    return scope


def _build_document(data: dict, document_id: str) -> AssetDocument:
    row = next(item for item in data["documents"] if item["id"] == document_id)
    document = AssetDocument(
        id=row["id"],
        container_id=row["container_id"],
        account_id=row["account_id"],
        added_by_account_id=row["added_by_account_id"],
        document_type=row["document_type"],
        s3_key=f"documents/{row['account_id']}/{row['container_id']}/{row['id']}",
        original_file_name_encrypted=encrypt_sensitive_value(
            row["original_file_name"],
            asset_service.get_settings().active_field_encryption_key,
        ),
        file_name_hash=asset_service._hash_file_name(row["original_file_name"]),
        file_size_bytes=row["file_size_bytes"],
        mime_type=row["mime_type"],
        upload_status=row["upload_status"],
        is_active=row["is_active"],
    )
    document.created_at = NOW
    document.updated_at = NOW
    return document


def _attach_detail(asset: Asset, detail_row: dict | None) -> None:
    if detail_row is None:
        return
    if asset.container_type == "BANK_RELATIONSHIP":
        detail = AssetBankDetail(container_id=asset.id)
        detail.account_type = detail_row.get("account_type")
        detail.account_number_masked = detail_row.get("account_number")
        detail.ifsc_code = detail_row.get("ifsc_code")
        asset.bank_detail = detail
    elif asset.container_type == "INSURANCE_POLICY":
        detail = AssetInsuranceDetail(container_id=asset.id)
        detail.policy_type = detail_row.get("policy_type")
        detail.policy_number_masked = detail_row.get("policy_number")
        detail.sum_assured = Decimal(detail_row["sum_assured"])
        asset.insurance_detail = detail
    elif asset.container_type == "REAL_ESTATE":
        detail = AssetRealEstateDetail(container_id=asset.id)
        detail.property_type = detail_row.get("property_type")
        detail.city = detail_row.get("city")
        detail.state = detail_row.get("state")
        asset.real_estate_detail = detail
    elif asset.container_type == "LOAN_ACCOUNT":
        detail = AssetLoanDetail(container_id=asset.id)
        detail.loan_type = detail_row.get("loan_type")
        detail.loan_account_masked = detail_row.get("loan_account")
        detail.outstanding_amount = Decimal(detail_row["outstanding_amount"])
        asset.loan_detail = detail
    elif asset.container_type == "BUSINESS_OWNERSHIP":
        detail = AssetBusinessDetail(container_id=asset.id)
        detail.business_type = detail_row.get("business_type")
        detail.business_name = detail_row.get("business_name")
        detail.ownership_percentage = Decimal(detail_row["ownership_percentage"])
        asset.business_detail = detail


def _build_asset(data: dict, asset_id: str) -> Asset:
    row = _asset_map(data)[asset_id]
    asset = Asset(
        id=row["id"],
        account_id=row["account_id"],
        added_by_account_id=row["added_by_account_id"],
        container_type=row["container_type"],
        institution_name=row["institution_name"],
        approximate_value=Decimal(row["approximate_value"]),
        notes=row["notes"],
        is_active=row["is_active"],
    )
    asset.created_at = NOW
    asset.updated_at = NOW
    _attach_detail(asset, data["asset_details"].get(asset_id))
    document_ids = [document["id"] for document in _document_rows_by_asset(data).get(asset_id, [])]
    asset.documents = [_build_document(data, document_id) for document_id in document_ids]
    return asset


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class _QueueSession:
    def __init__(
        self,
        *,
        scalar_results=None,
        scalars_results=None,
        execute_results=None,
        get_lookup=None,
        execute_assertion=None,
    ):
        self.scalar_results = list(scalar_results or [])
        self.scalars_results = list(scalars_results or [])
        self.execute_results = list(execute_results or [])
        self.get_lookup = dict(get_lookup or {})
        self.execute_assertion = execute_assertion
        self.added = []

    async def scalar(self, statement, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        if not self.scalar_results:
            raise AssertionError(f"Unexpected scalar() call for statement: {statement}")
        return self.scalar_results.pop(0)

    async def scalars(self, statement, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        if not self.scalars_results:
            raise AssertionError(f"Unexpected scalars() call for statement: {statement}")
        return _FakeScalarsResult(self.scalars_results.pop(0))

    async def execute(self, statement, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        if self.execute_assertion is not None:
            self.execute_assertion(statement)
        if not self.execute_results:
            raise AssertionError(f"Unexpected execute() call for statement: {statement}")
        return _FakeExecuteResult(self.execute_results.pop(0))

    async def get(self, model, key, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return self.get_lookup.get((model, key))

    def add(self, item):  # type: ignore[no-untyped-def]
        self.added.append(item)

    async def flush(self) -> None:
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = str(uuid4())


@pytest.fixture
def access_data() -> dict:
    return _load_fixture()


@pytest.mark.asyncio
async def test_resolve_resource_context_primary_can_use_own_workspace(access_data: dict) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-primary-001",
        profile_id="profile-primary-001-primary",
    )
    actor_profile = _build_profile(access_data, "profile-primary-001-primary")
    session = _QueueSession(scalar_results=[actor_profile])

    context = await resource_access_service.resolve_resource_context(
        session,  # type: ignore[arg-type]
        auth_context,
        profile_id="profile-primary-001-primary",
        primary_profile_id=None,
        require_write=False,
    )

    assert context.is_primary is True
    assert context.primary_account_id == "acct-primary-001"
    assert context.can_write is True
    assert context.profile_access is None


@pytest.mark.asyncio
async def test_resolve_resource_context_primary_rejects_other_workspace(access_data: dict) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-primary-001",
        profile_id="profile-primary-001-primary",
    )
    actor_profile = _build_profile(access_data, "profile-primary-001-primary")
    session = _QueueSession(scalar_results=[actor_profile])

    with pytest.raises(resource_access_service.HTTPException, match="own workspace"):
        await resource_access_service.resolve_resource_context(
            session,  # type: ignore[arg-type]
            auth_context,
            profile_id="profile-primary-001-primary",
            primary_profile_id="profile-primary-002-primary",
            require_write=False,
        )


@pytest.mark.asyncio
async def test_resolve_resource_context_advisor_with_active_access_can_write(
    access_data: dict,
) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-advisor-001",
        profile_id="profile-advisor-001-advisor",
    )
    actor_profile = _build_profile(access_data, "profile-advisor-001-advisor")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    active_access = _build_profile_access(access_data, "access-advisor-primary-001")
    session = _QueueSession(scalar_results=[actor_profile, primary_profile, active_access])

    context = await resource_access_service.resolve_resource_context(
        session,  # type: ignore[arg-type]
        auth_context,
        profile_id="profile-advisor-001-advisor",
        primary_profile_id="profile-primary-001-primary",
        require_write=True,
    )

    assert context.is_advisor is True
    assert context.can_write is True
    assert context.profile_access.id == "access-advisor-primary-001"
    assert context.primary_account_id == "acct-primary-001"


@pytest.mark.asyncio
async def test_resolve_resource_context_advisor_with_revoked_access_is_forbidden(
    access_data: dict,
) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-advisor-001",
        profile_id="profile-advisor-001-advisor",
    )
    actor_profile = _build_profile(access_data, "profile-advisor-001-advisor")
    primary_profile = _build_profile(access_data, "profile-primary-002-primary")
    session = _QueueSession(scalar_results=[actor_profile, primary_profile, None])

    with pytest.raises(resource_access_service.HTTPException, match="cannot access"):
        await resource_access_service.resolve_resource_context(
            session,  # type: ignore[arg-type]
            auth_context,
            profile_id="profile-advisor-001-advisor",
            primary_profile_id="profile-primary-002-primary",
            require_write=False,
        )


@pytest.mark.asyncio
async def test_resolve_resource_context_nominee_is_read_only(access_data: dict) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-nominee-001",
        profile_id="profile-nominee-001-nominee",
    )
    actor_profile = _build_profile(access_data, "profile-nominee-001-nominee")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    active_access = _build_profile_access(access_data, "access-nominee-primary-001")
    session = _QueueSession(scalar_results=[actor_profile, primary_profile, active_access])

    context = await resource_access_service.resolve_resource_context(
        session,  # type: ignore[arg-type]
        auth_context,
        profile_id="profile-nominee-001-nominee",
        primary_profile_id="profile-primary-001-primary",
        require_write=False,
    )

    assert context.is_nominee is True
    assert context.can_write is False
    assert context.profile_access.id == "access-nominee-primary-001"


@pytest.mark.asyncio
async def test_resolve_resource_context_nominee_write_is_forbidden(access_data: dict) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-nominee-001",
        profile_id="profile-nominee-001-nominee",
    )
    actor_profile = _build_profile(access_data, "profile-nominee-001-nominee")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    active_access = _build_profile_access(access_data, "access-nominee-primary-001")
    session = _QueueSession(scalar_results=[actor_profile, primary_profile, active_access])

    with pytest.raises(resource_access_service.HTTPException, match="cannot modify"):
        await resource_access_service.resolve_resource_context(
            session,  # type: ignore[arg-type]
            auth_context,
            profile_id="profile-nominee-001-nominee",
            primary_profile_id="profile-primary-001-primary",
            require_write=True,
        )


@pytest.mark.asyncio
async def test_create_asset_allows_advisor_and_assigns_primary_workspace_owner(
    access_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-advisor-001",
        profile_id="profile-advisor-001-advisor",
    )
    advisor_profile = _build_profile(access_data, "profile-advisor-001-advisor")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    access_context = resource_access_service.ResolvedResourceContext(
        actor_profile=advisor_profile,
        primary_profile=primary_profile,
        profile_access=_build_profile_access(access_data, "access-advisor-primary-001"),
        primary_account_id="acct-primary-001",
        can_write=True,
    )
    session = _QueueSession()

    async def fake_resolve_resource_context(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return access_context

    async def fake_get_asset_for_context(session_arg, **kwargs):  # type: ignore[no-untyped-def]
        asset = next(
            item
            for item in session_arg.added
            if isinstance(item, Asset) and item.id == kwargs["asset_id"]
        )
        detail = next(
            item
            for item in session_arg.added
            if isinstance(item, AssetBankDetail) and item.container_id == asset.id
        )
        asset.bank_detail = detail
        asset.documents = []
        asset.created_at = NOW
        asset.updated_at = NOW
        return asset, None

    monkeypatch.setattr(asset_service, "resolve_resource_context", fake_resolve_resource_context)
    monkeypatch.setattr(asset_service, "_get_asset_for_context", fake_get_asset_for_context)

    response = await asset_service.create_asset(
        session,  # type: ignore[arg-type]
        auth_context,
        AssetCreateRequest(
            profile_id="profile-advisor-001-advisor",
            primary_profile_id="profile-primary-001-primary",
            container_type="BANK_RELATIONSHIP",
            institution_name="Advisor Added Bank",
            detail={"account_type": "SAVINGS", "account_number": "1234567890"},
        ),
    )

    created_asset = next(item for item in session.added if isinstance(item, Asset))
    assert created_asset.account_id == "acct-primary-001"
    assert created_asset.added_by_account_id == "acct-advisor-001"
    assert response.can_edit is True
    assert response.institution_name == "Advisor Added Bank"


@pytest.mark.asyncio
async def test_get_asset_for_nominee_query_uses_canonical_nominee_scope(access_data: dict) -> None:
    asset = _build_asset(access_data, "asset-real-estate-001")
    nominee_profile = _build_profile(access_data, "profile-nominee-001-nominee")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    access_context = resource_access_service.ResolvedResourceContext(
        actor_profile=nominee_profile,
        primary_profile=primary_profile,
        profile_access=_build_profile_access(access_data, "access-nominee-primary-001"),
        primary_account_id="acct-primary-001",
        can_write=False,
    )

    def assert_nominee_query(statement) -> None:  # type: ignore[no-untyped-def]
        statement_text = str(statement)
        assert "account_nominee_scope" in statement_text
        assert "account_nominee" in statement_text
        assert "profile_access_scope" not in statement_text

    session = _QueueSession(
        execute_results=[[(asset, "VIEW_WITH_DOCUMENTS")]],
        execute_assertion=assert_nominee_query,
    )

    found_asset, permission = await asset_service._get_asset_for_context(
        session,  # type: ignore[arg-type]
        access_context=access_context,
        asset_id="asset-real-estate-001",
        include_inactive=False,
    )

    assert found_asset.id == "asset-real-estate-001"
    assert permission == "VIEW_WITH_DOCUMENTS"


def test_build_asset_response_hides_summary_only_nominee_detail_and_documents(
    access_data: dict,
) -> None:
    asset = _build_asset(access_data, "asset-bank-001")
    nominee_profile = _build_profile(access_data, "profile-nominee-001-nominee")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    access_context = resource_access_service.ResolvedResourceContext(
        actor_profile=nominee_profile,
        primary_profile=primary_profile,
        profile_access=_build_profile_access(access_data, "access-nominee-primary-001"),
        primary_account_id="acct-primary-001",
        can_write=False,
    )

    response = asset_service._build_asset_response(
        asset,
        access_context=access_context,
        access_permission="VIEW_SUMMARY",
    )

    assert response.detail is None
    assert response.documents == []
    assert response.access_permission == "VIEW_SUMMARY"


@pytest.mark.asyncio
async def test_list_asset_documents_nominee_with_docs_permission_returns_uploaded_only(
    access_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = _build_asset(access_data, "asset-real-estate-001")
    nominee_profile = _build_profile(access_data, "profile-nominee-001-nominee")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    access_context = resource_access_service.ResolvedResourceContext(
        actor_profile=nominee_profile,
        primary_profile=primary_profile,
        profile_access=_build_profile_access(access_data, "access-nominee-primary-001"),
        primary_account_id="acct-primary-001",
        can_write=False,
    )
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-nominee-001",
        profile_id="profile-nominee-001-nominee",
    )

    async def fake_resolve_resource_context(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return access_context

    async def fake_get_asset_for_context(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return asset, "VIEW_WITH_DOCUMENTS"

    monkeypatch.setattr(asset_service, "resolve_resource_context", fake_resolve_resource_context)
    monkeypatch.setattr(asset_service, "_get_asset_for_context", fake_get_asset_for_context)

    response = await asset_service.list_asset_documents(
        _QueueSession(),  # type: ignore[arg-type]
        auth_context,
        asset_id="asset-real-estate-001",
        profile_id="profile-nominee-001-nominee",
        primary_profile_id="profile-primary-001-primary",
        limit=20,
        offset=0,
    )

    assert [document.id for document in response.items] == ["doc-real-estate-001"]


@pytest.mark.asyncio
async def test_list_asset_documents_nominee_without_doc_permission_is_forbidden(
    access_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = _build_asset(access_data, "asset-insurance-001")
    nominee_profile = _build_profile(access_data, "profile-nominee-001-nominee")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    access_context = resource_access_service.ResolvedResourceContext(
        actor_profile=nominee_profile,
        primary_profile=primary_profile,
        profile_access=_build_profile_access(access_data, "access-nominee-primary-001"),
        primary_account_id="acct-primary-001",
        can_write=False,
    )
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-nominee-001",
        profile_id="profile-nominee-001-nominee",
    )

    async def fake_resolve_resource_context(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return access_context

    async def fake_get_asset_for_context(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return asset, "VIEW_FULL"

    monkeypatch.setattr(asset_service, "resolve_resource_context", fake_resolve_resource_context)
    monkeypatch.setattr(asset_service, "_get_asset_for_context", fake_get_asset_for_context)

    with pytest.raises(asset_service.HTTPException, match="cannot access asset documents"):
        await asset_service.list_asset_documents(
            _QueueSession(),  # type: ignore[arg-type]
            auth_context,
            asset_id="asset-insurance-001",
            profile_id="profile-nominee-001-nominee",
            primary_profile_id="profile-primary-001-primary",
            limit=20,
            offset=0,
        )


@pytest.mark.asyncio
async def test_list_asset_documents_primary_sees_failed_and_pending_rows(
    access_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = _build_asset(access_data, "asset-business-001")
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    access_context = resource_access_service.ResolvedResourceContext(
        actor_profile=primary_profile,
        primary_profile=primary_profile,
        profile_access=None,
        primary_account_id="acct-primary-001",
        can_write=True,
    )
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-primary-001",
        profile_id="profile-primary-001-primary",
    )

    async def fake_resolve_resource_context(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return access_context

    async def fake_get_asset_for_context(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return asset, None

    monkeypatch.setattr(asset_service, "resolve_resource_context", fake_resolve_resource_context)
    monkeypatch.setattr(asset_service, "_get_asset_for_context", fake_get_asset_for_context)

    response = await asset_service.list_asset_documents(
        _QueueSession(),  # type: ignore[arg-type]
        auth_context,
        asset_id="asset-business-001",
        profile_id="profile-primary-001-primary",
        primary_profile_id=None,
        limit=20,
        offset=0,
    )

    assert [document.id for document in response.items] == [
        "doc-business-failed-001",
        "doc-business-pending-001",
    ]


@pytest.mark.asyncio
async def test_update_nominee_visibility_grants_all_assigned_scope_rows(
    access_data: dict,
) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-primary-001",
        profile_id="profile-primary-001-primary",
    )
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    nominee = _build_nominee(access_data, "nominee-pending-001")
    scope = _build_scope(access_data, "scope-pending-assigned-visible-false")
    asset = _build_asset(access_data, "asset-bank-001")
    session = _QueueSession(
        scalar_results=[nominee, 1],
        scalars_results=[[scope], [scope], [asset]],
        get_lookup={(Profile, "profile-primary-001-primary"): primary_profile},
    )

    response = await nominee_service.update_nominee_visibility(
        session,  # type: ignore[arg-type]
        auth_context,
        "nominee-pending-001",
        NomineeVisibilityUpdateRequest(is_visible=True, all_assigned=True),
    )

    assert scope.is_visible is True
    assert scope.visibility_trigger_source == "PRIMARY_GRANTED"
    assert response[0].container_id == "asset-bank-001"


@pytest.mark.asyncio
async def test_update_nominee_visibility_revokes_selected_scope_rows_only(
    access_data: dict,
) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-primary-001",
        profile_id="profile-primary-001-primary",
    )
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    nominee = _build_nominee(access_data, "nominee-linked-001")
    target_scope = _build_scope(access_data, "scope-linked-docs-visible")
    untouched_scope = _build_scope(access_data, "scope-linked-full-visible")
    asset_real_estate = _build_asset(access_data, "asset-real-estate-001")
    asset_insurance = _build_asset(access_data, "asset-insurance-001")
    session = _QueueSession(
        scalar_results=[nominee, 2],
        scalars_results=[
            [target_scope, untouched_scope],
            [target_scope, untouched_scope],
            [asset_real_estate, asset_insurance],
        ],
        get_lookup={(Profile, "profile-primary-001-primary"): primary_profile},
    )

    response = await nominee_service.update_nominee_visibility(
        session,  # type: ignore[arg-type]
        auth_context,
        "nominee-linked-001",
        NomineeVisibilityUpdateRequest(
            is_visible=False,
            container_ids=["asset-real-estate-001"],
        ),
    )

    assert target_scope.is_visible is False
    assert target_scope.visibility_trigger_source == "PRIMARY_REVOKED"
    assert untouched_scope.is_visible is True
    assert {row.container_id for row in response} == {
        "asset-real-estate-001",
        "asset-insurance-001",
    }


@pytest.mark.asyncio
async def test_replace_nominee_scope_allows_linked_nominee(access_data: dict) -> None:
    auth_context = _build_auth_context(
        access_data,
        account_id="acct-primary-001",
        profile_id="profile-primary-001-primary",
    )
    primary_profile = _build_profile(access_data, "profile-primary-001-primary")
    nominee = _build_nominee(access_data, "nominee-linked-001")
    bank_asset = _build_asset(access_data, "asset-bank-001")
    existing_scope = _build_scope(access_data, "scope-linked-summary-visible")
    session = _QueueSession(
        scalar_results=[nominee, 1],
        scalars_results=[
            [bank_asset],
            [existing_scope],
            [existing_scope],
            [bank_asset],
        ],
        get_lookup={(Profile, "profile-primary-001-primary"): primary_profile},
    )

    response = await nominee_service.replace_nominee_scope(
        session,  # type: ignore[arg-type]
        auth_context,
        "nominee-linked-001",
        NomineeScopeReplaceRequest(
            scopes=[
                {"container_id": "asset-bank-001", "permission": "VIEW_SUMMARY"},
            ]
        ),
    )

    assert response[0].container_id == "asset-bank-001"
    assert existing_scope.is_active is True
