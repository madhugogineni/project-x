from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey

if TYPE_CHECKING:
    from db.models.auth import AccountAuthToken
    from db.models.inactivity import AccountInactivityState
    from db.models.nominee import AccountNominee
    from db.models.profile import Profile


class Account(UuidPrimaryKey, TimestampedModel, Base):
    """Single human identity. All personal data lives here."""

    __tablename__ = "account"

    # Login identifiers
    phone: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Legal identity
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # MALE | FEMALE | OTHER | PREFER_NOT_TO_SAY

    # Photo
    photo_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Account state — ACTIVE | SUSPENDED | DELETED
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # soft delete, never hard delete

    # Relationships
    addresses: Mapped[list["AccountAddress"]] = relationship(back_populates="account")
    pan: Mapped["AccountPan | None"] = relationship(back_populates="account", uselist=False)
    profiles: Mapped[list["Profile"]] = relationship(back_populates="account")
    auth_tokens: Mapped[list["AccountAuthToken"]] = relationship(back_populates="account")
    nominees_as_primary: Mapped[list["AccountNominee"]] = relationship(
        back_populates="primary_account",
        foreign_keys="AccountNominee.primary_account_id",
    )
    inactivity_state: Mapped["AccountInactivityState | None"] = relationship(
        back_populates="account", uselist=False
    )


class AccountAddress(UuidPrimaryKey, TimestampedModel, Base):
    """Current and permanent addresses per account."""

    __tablename__ = "account_address"
    __table_args__ = (
        UniqueConstraint("account_id", "address_type", name="uq_account_address_type"),
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    address_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CURRENT | PERMANENT

    address_line_1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)

    is_same_as_current: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=True
    )  # UX flag: permanent mirrors current

    account: Mapped[Account] = relationship(back_populates="addresses")


class AccountPan(UuidPrimaryKey, TimestampedModel, Base):
    """PAN card details. AES-256 encrypted at app layer — DB never sees plaintext."""

    __tablename__ = "account_pan"

    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    pan_number: Mapped[str] = mapped_column(Text, nullable=False)  # AES-256 encrypted
    name_on_pan: Mapped[str] = mapped_column(String(255), nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # SELF_DECLARED | THIRD_PARTY_API | MANUAL

    account: Mapped[Account] = relationship(back_populates="pan")
