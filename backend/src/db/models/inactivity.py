from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey

if TYPE_CHECKING:
    from db.models.account import Account


class AccountInactivityState(UuidPrimaryKey, TimestampedModel, Base):
    """Inactivity engine state per account.

    One row per account, created when the account is created.
    State is never reconstructed from audit logs — this table is the source of truth.

    State machine:
      ACTIVE          → no activity for 30 days  → REMINDER_SENT
      REMINDER_SENT   → no activity for 90 days  → ESCALATED
      ESCALATED       → grace period expires      → TRIGGERED
      TRIGGERED       → nominee KYC complete      → HOLD
                      → primary responds          → CANCELLED
      HOLD            → 7-day window expires      → RELEASED
                      → primary responds          → CANCELLED
      RELEASED        → terminal state (irreversible)
      CANCELLED       → resets to ACTIVE
    """

    __tablename__ = "account_inactivity_state"
    __table_args__ = (
        Index("idx_inactivity_state", "current_state"),
        Index("idx_inactivity_last_active", "last_active_at"),
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    current_state: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    # ACTIVE | REMINDER_SENT | ESCALATED | TRIGGERED | HOLD | RELEASED | CANCELLED

    # Activity tracking — mirrors max(last_used_at) from auth tokens
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Milestone timestamps — set once, never cleared
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalation_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trigger_initiated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    hold_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reminder_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="inactivity_state")
