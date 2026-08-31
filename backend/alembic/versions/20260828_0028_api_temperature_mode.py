"""add api credential temperature mode"""

import sqlalchemy as sa

from alembic import op

revision = "20260828_0028"
down_revision = "20260827_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_api_credentials",
        sa.Column(
            "temperature_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("model_api_credentials", "temperature_enabled")
