"""Add sellable catalog variants, inventory ledger, and explicit order state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0028"
down_revision: str | None = "20260729_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "products", sa.Column("sku", sa.String(100), nullable=False, server_default="")
    )
    op.add_column(
        "products", sa.Column("currency", sa.String(3), nullable=False, server_default="EGP")
    )
    op.add_column(
        "products", sa.Column("compare_at_price_numeric", sa.Numeric(12, 2), nullable=True)
    )
    op.add_column(
        "products", sa.Column("stock_policy", sa.String(20), nullable=False, server_default="deny")
    )
    op.add_column(
        "products", sa.Column("images_json", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column(
        "products", sa.Column("tax_json", sa.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "products", sa.Column("shipping_json", sa.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "products",
        sa.Column("source_of_truth", sa.String(20), nullable=False, server_default="local"),
    )
    op.add_column("products", sa.Column("source_provider", sa.String(40), nullable=True))
    op.add_column(
        "products", sa.Column("version", sa.Integer(), nullable=False, server_default="1")
    )
    op.execute("UPDATE products SET sku = product_id WHERE sku = ''")
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_source_of_truth", "products", ["source_of_truth"])
    op.create_index("ix_products_source_provider", "products", ["source_provider"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("product_pk", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("variant_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(160), nullable=False, server_default="Default"),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("price_numeric", sa.Numeric(12, 2), nullable=False),
        sa.Column("compare_at_price_numeric", sa.Numeric(12, 2), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_policy", sa.String(20), nullable=False, server_default="deny"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("product_pk", "variant_id", name="uq_product_variant_id"),
        sa.UniqueConstraint("store_id", "sku", name="uq_variant_store_sku"),
    )
    op.create_index("ix_product_variants_store_id", "product_variants", ["store_id"])
    op.create_index("ix_product_variants_product_pk", "product_variants", ["product_pk"])
    op.create_index("ix_product_variants_sku", "product_variants", ["sku"])
    op.create_index("ix_product_variants_status", "product_variants", ["status"])

    product = sa.table(
        "products",
        sa.column("id", sa.Integer()),
        sa.column("store_id", sa.String()),
        sa.column("product_id", sa.String()),
        sa.column("sku", sa.String()),
        sa.column("price_numeric", sa.Numeric()),
        sa.column("compare_at_price_numeric", sa.Numeric()),
        sa.column("stock", sa.Integer()),
        sa.column("stock_policy", sa.String()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    variants = sa.table(
        "product_variants",
        sa.column("store_id", sa.String()),
        sa.column("product_pk", sa.Integer()),
        sa.column("variant_id", sa.String()),
        sa.column("title", sa.String()),
        sa.column("sku", sa.String()),
        sa.column("options_json", sa.JSON()),
        sa.column("price_numeric", sa.Numeric()),
        sa.column("compare_at_price_numeric", sa.Numeric()),
        sa.column("stock", sa.Integer()),
        sa.column("stock_policy", sa.String()),
        sa.column("status", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        variants.insert().from_select(
            [
                "store_id",
                "product_pk",
                "variant_id",
                "title",
                "sku",
                "options_json",
                "price_numeric",
                "compare_at_price_numeric",
                "stock",
                "stock_policy",
                "status",
                "version",
                "created_at",
                "updated_at",
            ],
            sa.select(
                product.c.store_id,
                product.c.id,
                sa.literal("default"),
                sa.literal("Default"),
                product.c.sku,
                sa.cast(sa.literal("{}"), sa.JSON()),
                product.c.price_numeric,
                product.c.compare_at_price_numeric,
                product.c.stock,
                product.c.stock_policy,
                sa.literal("active"),
                sa.literal(1),
                product.c.created_at,
                product.c.updated_at,
            ),
        )
    )

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.String(64), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("product_pk", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column(
            "variant_pk", sa.Integer(), sa.ForeignKey("product_variants.id"), nullable=True
        ),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("reference_type", sa.String(40), nullable=False, server_default=""),
        sa.Column("reference_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("actor_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "idempotency_key", name="uq_inventory_idempotency"),
    )
    op.create_index("ix_inventory_transactions_store_id", "inventory_transactions", ["store_id"])
    op.create_index(
        "ix_inventory_transactions_product_pk", "inventory_transactions", ["product_pk"]
    )
    op.create_index(
        "ix_inventory_transactions_variant_pk", "inventory_transactions", ["variant_pk"]
    )
    op.create_index("ix_inventory_transactions_reason", "inventory_transactions", ["reason"])
    op.create_index(
        "ix_inventory_transactions_reference_id", "inventory_transactions", ["reference_id"]
    )
    op.create_index(
        "ix_inventory_transactions_actor_user_id",
        "inventory_transactions",
        ["actor_user_id"],
    )

    op.add_column(
        "orders",
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"),
    )
    op.add_column(
        "orders",
        sa.Column(
            "fulfillment_status", sa.String(20), nullable=False, server_default="unfulfilled"
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "shipping_total_numeric", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "orders",
        sa.Column("tax_total_numeric", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "orders",
        sa.Column(
            "provider_references_json", sa.JSON(), nullable=False, server_default="{}"
        ),
    )
    op.add_column("orders", sa.Column("idempotency_key", sa.String(160), nullable=True))
    op.create_index("ix_orders_payment_status", "orders", ["payment_status"])
    op.create_index("ix_orders_fulfillment_status", "orders", ["fulfillment_status"])
    op.create_unique_constraint(
        "uq_order_idempotency", "orders", ["store_id", "idempotency_key"]
    )

    op.add_column(
        "order_items",
        sa.Column("variant_pk", sa.Integer(), sa.ForeignKey("product_variants.id"), nullable=True),
    )
    op.add_column("order_items", sa.Column("variant_id", sa.String(64), nullable=True))
    op.add_column(
        "order_items", sa.Column("sku", sa.String(100), nullable=False, server_default="")
    )
    op.add_column(
        "order_items", sa.Column("options_json", sa.JSON(), nullable=False, server_default="{}")
    )


def downgrade() -> None:
    op.drop_column("order_items", "options_json")
    op.drop_column("order_items", "sku")
    op.drop_column("order_items", "variant_id")
    op.drop_column("order_items", "variant_pk")
    op.drop_constraint("uq_order_idempotency", "orders", type_="unique")
    op.drop_index("ix_orders_fulfillment_status", table_name="orders")
    op.drop_index("ix_orders_payment_status", table_name="orders")
    op.drop_column("orders", "idempotency_key")
    op.drop_column("orders", "provider_references_json")
    op.drop_column("orders", "tax_total_numeric")
    op.drop_column("orders", "shipping_total_numeric")
    op.drop_column("orders", "fulfillment_status")
    op.drop_column("orders", "payment_status")
    op.drop_table("inventory_transactions")
    op.drop_table("product_variants")
    op.drop_index("ix_products_source_provider", table_name="products")
    op.drop_index("ix_products_source_of_truth", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_column("products", "version")
    op.drop_column("products", "source_provider")
    op.drop_column("products", "source_of_truth")
    op.drop_column("products", "shipping_json")
    op.drop_column("products", "tax_json")
    op.drop_column("products", "images_json")
    op.drop_column("products", "stock_policy")
    op.drop_column("products", "compare_at_price_numeric")
    op.drop_column("products", "currency")
    op.drop_column("products", "sku")
