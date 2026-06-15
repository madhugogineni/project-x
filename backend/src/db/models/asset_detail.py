"""Typed detail tables for each asset type.

Each table has a one-to-one relationship with asset via container_id UNIQUE.

Sensitive reference numbers follow the encrypted + masked convention:
  field_encrypted  TEXT       — AES-256 encrypted at app layer, DB never sees plaintext
  field_masked     VARCHAR    — partial value only e.g. XXXXXX3210

Display rule:
  - Always show masked value — no decryption needed
  - Decrypt only when permission = VIEW_WITH_DOCUMENTS AND is_visible = TRUE
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey

if TYPE_CHECKING:
    from db.models.account import Account
    from db.models.asset import Asset


class AssetBankDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Bank accounts: savings, current, FD, RD, lockers, foreign accounts."""

    __tablename__ = "asset_bank_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    account_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_number_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    account_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # SAVINGS | CURRENT | FD | RD | LOCKER | FOREIGN
    ifsc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)

    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # FD / RD
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="bank_detail")


class AssetDematDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Demat accounts: shares, bonds, ETFs, REITs, SGBs, PMS-linked holdings."""

    __tablename__ = "asset_demat_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    dp_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    client_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_id_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    depository: Mapped[str | None] = mapped_column(String(10), nullable=True)  # NSDL | CDSL
    broker_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="demat_detail")


class AssetMutualFundDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Mutual fund folios not held in demat. Transmission via AMC or RTA."""

    __tablename__ = "asset_mutual_fund_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    folio_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    folio_number_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    amc_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rta_name: Mapped[str | None] = mapped_column(String(50), nullable=True)  # CAMS | KFINTECH

    container: Mapped["Asset"] = relationship(back_populates="mutual_fund_detail")


class AssetRetirementDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Retirement accounts: EPF, PPF, NPS, superannuation, pension."""

    __tablename__ = "asset_retirement_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    account_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # EPF | PPF | NPS | SUPERANNUATION | PENSION

    reference_number_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # UAN for EPF, PRAN for NPS etc.
    reference_number_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    employer_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # relevant for EPF
    fund_manager: Mapped[str | None] = mapped_column(String(255), nullable=True)  # relevant for NPS

    container: Mapped["Asset"] = relationship(back_populates="retirement_detail")


class AssetInsuranceDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Insurance policies: life, health, accident, property. One row per policy."""

    __tablename__ = "asset_insurance_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    policy_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_number_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    policy_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # LIFE | HEALTH | ACCIDENT | PROPERTY
    sum_assured: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    premium_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    premium_frequency: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # MONTHLY | QUARTERLY | ANNUAL | SINGLE
    policy_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active_policy: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="insurance_detail")


class AssetRealEstateDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Real estate: residential, commercial, land, agricultural property."""

    __tablename__ = "asset_real_estate_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    property_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # RESIDENTIAL | COMMERCIAL | LAND | AGRICULTURAL
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    registration_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_number_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    co_owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ownership_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="real_estate_detail")


class AssetLoanDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Loans and guarantees: home, personal, business, gold, vehicle."""

    __tablename__ = "asset_loan_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    loan_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # HOME | PERSONAL | BUSINESS | GOLD | VEHICLE | GUARANTEE
    loan_account_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    loan_account_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    outstanding_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    emi_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    emi_frequency: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # MONTHLY | QUARTERLY
    loan_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    loan_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="loan_detail")


class AssetBusinessDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Business ownership: private limited, LLP, partnership, proprietorship."""

    __tablename__ = "asset_business_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    business_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # PRIVATE_LIMITED | LLP | PARTNERSHIP | PROPRIETORSHIP
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ownership_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    cin_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    cin_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    registered_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="business_detail")


class AssetGovtSavingsDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Government savings schemes: NSC, SSY, SCSS, post office FD/RD, KVP."""

    __tablename__ = "asset_govt_savings_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    scheme_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # NSC | SSY | SCSS | POST_OFFICE_FD | POST_OFFICE_RD | KVP | OTHER
    account_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_number_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)

    post_office_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="govt_savings_detail")


class AssetCryptoDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Crypto assets: exchange accounts and self-custody wallets.

    No private keys. No seed phrases. Ever.
    """

    __tablename__ = "asset_crypto_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    custody_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # EXCHANGE | SELF_CUSTODY
    exchange_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    registered_email_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # exchange login identifier only
    registered_email_masked: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. ra***@gmail.com

    wallet_address: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # public address only, not a secret

    container: Mapped["Asset"] = relationship(back_populates="crypto_detail")


class AssetReceivableDetail(UuidPrimaryKey, TimestampedModel, Base):
    """Receivables: employer dues, legal settlements, earnouts, refundable deposits."""

    __tablename__ = "asset_receivable_detail"

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    receivable_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # EMPLOYER_DUES | LEGAL_SETTLEMENT | EARNOUT | DEPOSIT | OTHER
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    container: Mapped["Asset"] = relationship(back_populates="receivable_detail")


class AssetDocument(UuidPrimaryKey, Base):
    """Documents attached to any asset. Encrypted before S3 upload.

    No updated_at — documents are immutable once uploaded (is_active soft-delete only).
    """

    __tablename__ = "asset_document"
    __table_args__ = (
        Index("idx_asset_document_container", "container_id"),
        Index("idx_asset_document_account", "account_id"),
        Index("idx_asset_document_added_by", "added_by_account_id"),
    )

    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), nullable=False
    )
    # Owner of this document
    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    # Who uploaded this document (primary or advisor)
    added_by_account_id: Mapped[str] = mapped_column(ForeignKey("account.id"), nullable=False)

    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # POLICY_DOCUMENT | PROPERTY_PAPER | INVESTMENT_STATEMENT |
    # LEGAL_AGREEMENT | ACCOUNT_STATEMENT | OTHER

    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_file_name_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    file_name_hash: Mapped[str] = mapped_column(Text, nullable=False)  # SHA-256 hash
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    upload_status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING_UPLOAD",
        nullable=False,
    )  # PENDING_UPLOAD | UPLOADED | FAILED

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    container: Mapped["Asset"] = relationship(back_populates="documents")
    account: Mapped["Account"] = relationship(foreign_keys=[account_id])
    added_by_account: Mapped["Account"] = relationship(foreign_keys=[added_by_account_id])
