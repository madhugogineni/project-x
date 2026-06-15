from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey

if TYPE_CHECKING:
    from db.models.account import Account
    from db.models.nominee import ProfileAccess


class ProfileType(str, Enum):
    PRIMARY = "PRIMARY"
    ADVISOR = "ADVISOR"
    NOMINEE = "NOMINEE"


class Profile(UuidPrimaryKey, TimestampedModel, Base):
    """Thin access context container. No personal data lives here.

    profile_type is the source of truth for access behaviour — NOMINEE vs ADVISOR.
    Each account can have at most one profile per type.
    """

    __tablename__ = "profile"
    __table_args__ = (
        UniqueConstraint("account_id", "profile_type", name="uq_profile_account_type"),
        Index("idx_profile_account", "account_id"),
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    profile_type: Mapped[ProfileType] = mapped_column(
        String(20), nullable=False
    )  # PRIMARY | ADVISOR | NOMINEE
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="profiles")
    access_as_accessor: Mapped[list["ProfileAccess"]] = relationship(
        back_populates="accessor_profile",
        foreign_keys="ProfileAccess.accessor_profile_id",
    )
    access_as_primary: Mapped[list["ProfileAccess"]] = relationship(
        back_populates="primary_profile",
        foreign_keys="ProfileAccess.primary_profile_id",
    )
