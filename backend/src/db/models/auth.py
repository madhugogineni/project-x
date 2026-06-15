from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from db.models.base import Base, UuidPrimaryKey

if TYPE_CHECKING:
    from db.models.account import Account
    from db.models.profile import Profile


class AccountOtpSession(UuidPrimaryKey, Base):
    """OTP session for login and sensitive operations.

    phone is NOT a foreign key — supports pre-registration flow.
    """

    __tablename__ = "account_otp_session"
    __table_args__ = (Index("idx_otp_phone_purpose", "phone", "purpose"),)

    phone: Mapped[str] = mapped_column(String(15), nullable=False)

    otp_hash: Mapped[str] = mapped_column(Text, nullable=False)  # bcrypt hash only
    purpose: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # SIGNUP | LOGIN | PHONE_CHANGE | ACCOUNT_DELETE

    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    resend_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    max_resends: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # null = not yet used
    verified_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


class AccountAuthToken(UuidPrimaryKey, Base):
    """JWT jti registry for server-side token revocation.

    JWT validation flow:
      - Verify JWT signature (no DB hit)
      - Extract jti from payload
      - Lookup jti in this table
          revoked_at IS NOT NULL → reject 401
          expires_at < now()    → reject 401
          otherwise             → allow, update last_used_at
    """

    __tablename__ = "account_auth_token"
    __table_args__ = (
        Index("idx_auth_token_account", "account_id"),
        Index("idx_auth_token_jti", "jti"),
        Index("idx_auth_token_session", "account_id", "session_id"),
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )

    jti: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), unique=True, nullable=False
    )  # JWT ID claim — revocation key
    session_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), nullable=False
    )  # logical login session shared across access/refresh rows
    token_type: Mapped[str] = mapped_column(
        String(20), default="ACCESS", nullable=False
    )  # ACCESS | REFRESH

    active_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile.id", ondelete="SET NULL"), nullable=True
    )

    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # LOGOUT | FORCE_REVOKE | PHONE_CHANGED | SUSPICIOUS_ACTIVITY

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # primary input for inactivity engine

    account: Mapped["Account"] = relationship(back_populates="auth_tokens")
    active_profile: Mapped["Profile | None"] = relationship(foreign_keys=[active_profile_id])
