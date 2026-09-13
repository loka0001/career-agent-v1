"""Generated content slice of models.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.model_groups.shared import utc_now

if TYPE_CHECKING:
    from app.db.model_groups.catalog import ProductModel


class MarketingPackModel(Base):
    __tablename__ = "marketing_packs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    product_pk: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    facebook_message: Mapped[str] = mapped_column(Text)
    instagram_caption: Mapped[str] = mapped_column(Text)
    hashtags_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_url: Mapped[str] = mapped_column(Text)
    validation_warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(20), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    approved_content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    product: Mapped[ProductModel] = relationship(back_populates="marketing_packs")
    publications: Mapped[list[PublicationModel]] = relationship(
        back_populates="marketing_pack", cascade="all, delete-orphan"
    )


class PublicationModel(Base):
    __tablename__ = "publications"
    __table_args__ = (
        UniqueConstraint(
            "marketing_pack_id", "platform", "request_id", name="uq_publication_idempotency"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    marketing_pack_id: Mapped[int] = mapped_column(ForeignKey("marketing_packs.id"), index=True)
    platform: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permalink: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    marketing_pack: Mapped[MarketingPackModel] = relationship(back_populates="publications")


class PolicyModel(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("store_id", "source_ref", name="uq_policy_source"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    policy_type: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(String(255), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class SalesQueryModel(Base):
    __tablename__ = "sales_queries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    parsed_need_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    recommended_product_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    response_text: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
