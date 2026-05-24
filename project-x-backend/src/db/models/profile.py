from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey


class ProfileType(str, Enum):
    PRIMARY = "PRIMARY"
    ADVISOR = "ADVISOR"
    NOMINEE = "NOMINEE"


class Account(UuidPrimaryKey, TimestampedModel, Base):
    __tablename__ = "accounts"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)

    profiles: Mapped[list["Profile"]] = relationship(back_populates="account")


class Profile(UuidPrimaryKey, TimestampedModel, Base):
    __tablename__ = "profiles"

    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    profile_type: Mapped[ProfileType] = mapped_column(
        SqlEnum(ProfileType, name="profile_type"),
        nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)

    account: Mapped[Account] = relationship(back_populates="profiles")
    outgoing_access_links: Mapped[list["ProfileAccess"]] = relationship(
        back_populates="granted_by_profile",
        foreign_keys="ProfileAccess.granted_by_profile_id"
    )
    incoming_access_links: Mapped[list["ProfileAccess"]] = relationship(
        back_populates="granted_to_profile",
        foreign_keys="ProfileAccess.granted_to_profile_id"
    )


class ProfileAccess(UuidPrimaryKey, TimestampedModel, Base):
    __tablename__ = "profile_access"
    __table_args__ = (
        UniqueConstraint(
            "granted_by_profile_id",
            "granted_to_profile_id",
            name="uq_profile_access_pair"
        ),
    )

    granted_by_profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id"),
        nullable=False
    )
    granted_to_profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id"),
        nullable=False
    )
    access_reason: Mapped[str] = mapped_column(String(80), nullable=False)

    granted_by_profile: Mapped[Profile] = relationship(
        back_populates="outgoing_access_links",
        foreign_keys=[granted_by_profile_id]
    )
    granted_to_profile: Mapped[Profile] = relationship(
        back_populates="incoming_access_links",
        foreign_keys=[granted_to_profile_id]
    )
