"""Audit domain models.

audit_log is partitioned by year in PostgreSQL. The ORM model maps to the
parent table; yearly partitions (audit_log_2025, audit_log_2026, …) are managed
via DDL outside the ORM. Rows are INSERT-only — no UPDATE, no DELETE, ever.

audit_resource_access captures the first access per actor per resource after
the inactivity trigger fires.
"""

from datetime import datetime

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from db.models.base import Base, UuidPrimaryKey


class AuditLog(Base):
    """Append-only audit log, partitioned by year.

    Composite PK (id, created_at) is required for PostgreSQL range partitioning.
    Do NOT issue UPDATE or DELETE against this table.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_account_id", "account_id", "created_at"),
        Index("idx_audit_actor", "actor_account_id", "created_at"),
        Index("idx_audit_event_type", "event_type", "created_at"),
        Index("idx_audit_entity", "entity_type", "entity_id", "created_at"),
        Index("idx_audit_domain", "event_domain", "created_at"),
        # postgresql_partition_by is set via raw DDL — not expressed here
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, nullable=False)

    # Whose account this event relates to (always the primary/owner)
    account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)

    # Who performed the action (NULL = system)
    actor_account_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)
    actor_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # USER | NOMINEE | ADVISOR | SYSTEM

    profile_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)

    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    event_domain: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # AUTH | ACCOUNT | NOMINEE_ACCESS | ASSET | TRIGGER | DOCUMENT

    entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # ACCOUNT | PROFILE | NOMINEE | ASSET_CONTAINER | DOCUMENT | TRIGGER | ACCESS_SCOPE
    entity_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True)

    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default="SUCCESS", nullable=False
    )  # SUCCESS | FAILURE | BLOCKED
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Part of composite PK for partitioning
    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        primary_key=True,
        nullable=False,
    )


class AuditResourceAccess(UuidPrimaryKey, Base):
    """First access per actor per resource after the inactivity trigger fires.

    Insert pattern — first access only:
      INSERT INTO audit_resource_access (...)
      VALUES (...)
      ON CONFLICT (actor_account_id, entity_type, entity_id) DO NOTHING;
    """

    __tablename__ = "audit_resource_access"
    __table_args__ = (
        UniqueConstraint(
            "actor_account_id",
            "entity_type",
            "entity_id",
            name="uq_resource_access_actor_entity",
        ),
        Index("idx_resource_access_account", "account_id"),
        Index("idx_resource_access_actor", "actor_account_id"),
        Index("idx_resource_access_entity", "entity_type", "entity_id"),
    )

    account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    actor_account_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # NOMINEE | ADVISOR

    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ASSET_CONTAINER | DOCUMENT
    entity_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)

    access_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # VIEW_SUMMARY | VIEW_FULL | VIEW_WITH_DOCUMENTS

    first_accessed_at: Mapped[datetime] = mapped_column("first_accessed_at", nullable=False)

    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
