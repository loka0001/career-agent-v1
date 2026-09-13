"""Initial Commerce AI schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260722_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("default_language", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_stores_slug", "stores", ["slug"])
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("product_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("price_numeric", sa.Numeric(12, 2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("benefits_json", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image_summary", sa.Text(), nullable=False),
        sa.Column("original_image_url", sa.Text(), nullable=False),
        sa.Column("public_image_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "product_id", name="uq_product_store_id"),
    )
    op.create_index("ix_products_store_id", "products", ["store_id"])
    op.create_index("ix_products_product_id", "products", ["product_id"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_status", "products", ["status"])
    op.create_table(
        "marketing_packs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("product_pk", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("facebook_message", sa.Text(), nullable=False),
        sa.Column("instagram_caption", sa.Text(), nullable=False),
        sa.Column("hashtags_json", sa.JSON(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("validation_warnings_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(320), nullable=True),
        sa.Column("approved_content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_marketing_packs_store_id", "marketing_packs", ["store_id"])
    op.create_index("ix_marketing_packs_product_pk", "marketing_packs", ["product_pk"])
    op.create_index("ix_marketing_packs_status", "marketing_packs", ["status"])
    op.create_table(
        "publications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "marketing_pack_id",
            sa.Integer(),
            sa.ForeignKey("marketing_packs.id"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("permalink", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_status", sa.String(100), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "marketing_pack_id", "platform", "request_id", name="uq_publication_idempotency"
        ),
    )
    op.create_index("ix_publications_marketing_pack_id", "publications", ["marketing_pack_id"])
    op.create_index("ix_publications_status", "publications", ["status"])
    op.create_index("ix_publications_request_id", "publications", ["request_id"])
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("policy_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "source_ref", name="uq_policy_source"),
    )
    op.create_index("ix_policies_store_id", "policies", ["store_id"])
    op.create_index("ix_policies_policy_type", "policies", ["policy_type"])
    op.create_index("ix_policies_source_ref", "policies", ["source_ref"])
    op.create_table(
        "sales_queries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("parsed_need_json", sa.JSON(), nullable=False),
        sa.Column("recommended_product_ids_json", sa.JSON(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sales_queries_store_id", "sales_queries", ["store_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("sales_queries")
    op.drop_table("policies")
    op.drop_table("publications")
    op.drop_table("marketing_packs")
    op.drop_table("products")
    op.drop_table("stores")
