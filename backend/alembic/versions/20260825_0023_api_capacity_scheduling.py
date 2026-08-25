"""add api center capacity scheduling fields"""

import sqlalchemy as sa

from alembic import op

revision = "20260825_0023"
down_revision = "20260824_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_api_credentials",
        sa.Column(
            "max_concurrency",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("model_api_credentials", "max_concurrency")
