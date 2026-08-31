"""add api credential capability profile"""

import sqlalchemy as sa

from alembic import op

revision = "20260828_0030"
down_revision = "20260828_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_api_credentials",
        sa.Column(
            "capability_profile_json",
            sa.Text(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("model_api_credentials", "capability_profile_json")
