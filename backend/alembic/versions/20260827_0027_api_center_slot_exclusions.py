"""add api center routing slot exclusions"""

import sqlalchemy as sa

from alembic import op

revision = "20260827_0027"
down_revision = "20260826_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_routing_slots",
        sa.Column(
            "excluded_credential_ids_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("model_routing_slots", "excluded_credential_ids_json")
