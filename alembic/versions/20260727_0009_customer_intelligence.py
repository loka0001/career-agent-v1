"""Customer merge lineage."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0009"
down_revision: str | None = "20260727_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("customers") as batch:
        batch.add_column(
            sa.Column("merged_into_id", sa.Integer(), nullable=True)
        )
        batch.create_foreign_key(
            "fk_customers_merged_into",
            "customers",
            ["merged_into_id"],
            ["id"],
        )
        batch.create_index("ix_customers_merged_into_id", ["merged_into_id"])


def downgrade() -> None:
    with op.batch_alter_table("customers") as batch:
        batch.drop_constraint("fk_customers_merged_into", type_="foreignkey")
        batch.drop_index("ix_customers_merged_into_id")
        batch.drop_column("merged_into_id")
