"""Add origin-bound publishable keys for browser integrations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0022"
down_revision: str | None = "20260728_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.add_column(
            sa.Column(
                "key_type",
                sa.String(20),
                nullable=False,
                server_default="publishable",
            )
        )
        batch.add_column(
            sa.Column(
                "allowed_origins_json",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )
        batch.create_index("ix_api_keys_key_type", ["key_type"])


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch:
        batch.drop_index("ix_api_keys_key_type")
        batch.drop_column("allowed_origins_json")
        batch.drop_column("key_type")
