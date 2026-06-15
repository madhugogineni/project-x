from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey

if TYPE_CHECKING:
    from db.models.asset_detail import (
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
    from db.models.nominee import AccountNomineeScope


class Asset(UuidPrimaryKey, TimestampedModel, Base):
    """Universal parent record for every asset type.

    Advisor vs primary distinction:
      account_id == added_by_account_id  → primary added this asset themselves
      account_id != added_by_account_id  → advisor added this asset on primary's behalf
    """

    __tablename__ = "asset"
    __table_args__ = (
        Index("idx_asset_account", "account_id"),
        Index("idx_asset_type", "account_id", "container_type"),
        Index("idx_asset_added_by", "added_by_account_id"),
    )

    # Owner of this asset
    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    # Who created this record (primary or advisor)
    added_by_account_id: Mapped[str] = mapped_column(ForeignKey("account.id"), nullable=False)

    container_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # BANK_RELATIONSHIP | DEMAT_ACCOUNT | MUTUAL_FUND_FOLIO | RETIREMENT_ACCOUNT |
    # INSURANCE_POLICY | REAL_ESTATE | LOAN_ACCOUNT | BUSINESS_OWNERSHIP |
    # GOVERNMENT_SAVINGS_SCHEME | CRYPTO_ACCOUNT | RECEIVABLE_CLAIM

    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approximate_value: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )  # user-declared, not verified
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships to typed detail tables (one-to-one each)
    bank_detail: Mapped[AssetBankDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    demat_detail: Mapped[AssetDematDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    mutual_fund_detail: Mapped[AssetMutualFundDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    retirement_detail: Mapped[AssetRetirementDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    insurance_detail: Mapped[AssetInsuranceDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    real_estate_detail: Mapped[AssetRealEstateDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    loan_detail: Mapped[AssetLoanDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    business_detail: Mapped[AssetBusinessDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    govt_savings_detail: Mapped[AssetGovtSavingsDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    crypto_detail: Mapped[AssetCryptoDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    receivable_detail: Mapped[AssetReceivableDetail | None] = relationship(
        back_populates="container", uselist=False
    )
    documents: Mapped[list[AssetDocument]] = relationship(back_populates="container")
    nominee_scope_rows: Mapped[list[AccountNomineeScope]] = relationship(
        foreign_keys="AccountNomineeScope.container_id"
    )
