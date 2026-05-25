from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.models.base import Base, TimestampedModel, UuidPrimaryKey


class AssetContainer(UuidPrimaryKey, TimestampedModel, Base):
    __tablename__ = "asset_containers"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(160), nullable=False)
    container_type: Mapped[str] = mapped_column(String(80), nullable=False)
    reference_note: Mapped[str | None] = mapped_column(Text(), nullable=True)

    assets: Mapped[list["Asset"]] = relationship(back_populates="container")


class Asset(UuidPrimaryKey, TimestampedModel, Base):
    __tablename__ = "assets"

    container_id: Mapped[str] = mapped_column(ForeignKey("asset_containers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    approximate_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    nominee_recorded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    container: Mapped[AssetContainer] = relationship(back_populates="assets")
    documents: Mapped[list["Document"]] = relationship(back_populates="asset")


class Document(UuidPrimaryKey, TimestampedModel, Base):
    __tablename__ = "documents"

    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    encryption_state: Mapped[str] = mapped_column(String(40), nullable=False)

    asset: Mapped[Asset] = relationship(back_populates="documents")
