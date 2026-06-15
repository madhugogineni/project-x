from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey

if TYPE_CHECKING:
    from db.models.account import Account
    from db.models.profile import Profile


class AccountNominee(UuidPrimaryKey, TimestampedModel, Base):
    """Nominees declared by a primary user.

    Advisor vs primary distinction:
      primary_account_id == added_by_account_id → primary added this nominee
      primary_account_id != added_by_account_id → advisor added on primary's behalf
    """

    __tablename__ = "account_nominee"
    __table_args__ = (
        Index("idx_nominee_primary", "primary_account_id"),
        Index("idx_nominee_added_by", "added_by_account_id"),
        Index("idx_nominee_linked", "linked_account_id"),
        Index("idx_nominee_profile", "nominee_profile_id"),
    )

    primary_account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    added_by_account_id: Mapped[str] = mapped_column(ForeignKey("account.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    nominee_relationship: Mapped[str] = mapped_column(
        "relationship", String(50), nullable=False
    )  # SPOUSE | CHILD | PARENT | SIBLING | OTHER
    phone: Mapped[str | None] = mapped_column(String(15), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    share_percentage: Mapped[float | None] = mapped_column(
        "share_percentage",
        nullable=True,
    )  # Informational only — not legally binding

    # Lifecycle — PENDING | INVITED | LINKED | REMOVED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    # Set once nominee creates an account
    linked_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"), nullable=True
    )
    nominee_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile.id", ondelete="SET NULL"), nullable=True
    )
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    primary_account: Mapped[Account] = relationship(
        back_populates="nominees_as_primary",
        foreign_keys=[primary_account_id],
    )
    added_by_account: Mapped[Account] = relationship(foreign_keys=[added_by_account_id])
    linked_account: Mapped[Account | None] = relationship(foreign_keys=[linked_account_id])
    nominee_profile: Mapped[Profile | None] = relationship(foreign_keys=[nominee_profile_id])
    scope_rows: Mapped[list[AccountNomineeScope]] = relationship(back_populates="account_nominee")


class AccountNomineeScope(UuidPrimaryKey, TimestampedModel, Base):
    """Canonical asset scope and visibility state for nominees.

    The nominee row may later link to a real account/profile, but nominee resource
    visibility and permission continue to live here.
    """

    __tablename__ = "account_nominee_scope"
    __table_args__ = (
        UniqueConstraint(
            "account_nominee_id", "container_id", name="uq_nominee_scope_nominee_container"
        ),
        Index("idx_nominee_scope_nominee", "account_nominee_id"),
        Index("idx_nominee_scope_container", "container_id"),
        Index("idx_nominee_scope_visible", "is_visible"),
        Index("idx_nominee_scope_active", "is_active"),
    )

    account_nominee_id: Mapped[str] = mapped_column(
        ForeignKey("account_nominee.id", ondelete="CASCADE"), nullable=False
    )
    added_by_account_id: Mapped[str] = mapped_column(ForeignKey("account.id"), nullable=False)
    container_id: Mapped[str] = mapped_column(
        ForeignKey("asset.id", ondelete="CASCADE"), nullable=False
    )

    permission: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # VIEW_SUMMARY | VIEW_FULL | VIEW_WITH_DOCUMENTS

    # Scope rows are never deleted, only deactivated
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Visibility gate — flipped by manual sharing or inactivity release
    is_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visibility_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    visibility_trigger_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # PRIMARY_GRANTED | PRIMARY_REVOKED | INACTIVITY_TRIGGER

    account_nominee: Mapped[AccountNominee] = relationship(back_populates="scope_rows")
    added_by_account: Mapped[Account] = relationship(foreign_keys=[added_by_account_id])


class ProfileAccess(UuidPrimaryKey, TimestampedModel, Base):
    """Formal access relationship between an accessor profile and a primary profile.

    Created when a nominee's account is linked, or when an advisor is invited.
    Access behaviour (immediate vs trigger-gated) is determined by profile.profile_type.
    """

    __tablename__ = "profile_access"
    __table_args__ = (
        UniqueConstraint(
            "accessor_profile_id", "primary_profile_id", name="uq_profile_access_pair"
        ),
        CheckConstraint(
            "accessor_profile_id <> primary_profile_id",
            name="chk_profile_access_no_self",
        ),
        Index("idx_profile_access_primary", "primary_profile_id"),
        Index("idx_profile_access_accessor", "accessor_profile_id"),
    )

    # Must be ADVISOR or NOMINEE profile
    accessor_profile_id: Mapped[str] = mapped_column(
        ForeignKey("profile.id", ondelete="CASCADE"), nullable=False
    )
    # Must be PRIMARY profile
    primary_profile_id: Mapped[str] = mapped_column(
        ForeignKey("profile.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="ACTIVE", nullable=False
    )  # ACTIVE | REVOKED

    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    accessor_profile: Mapped[Profile] = relationship(
        back_populates="access_as_accessor",
        foreign_keys=[accessor_profile_id],
    )
    primary_profile: Mapped[Profile] = relationship(
        back_populates="access_as_primary",
        foreign_keys=[primary_profile_id],
    )
