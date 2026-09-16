"""Daily business feedback completion date.

Revision ID: 20260916_0043
Revises: 20260916_0042
"""

import sqlalchemy as sa

from alembic import op

revision = "20260916_0043"
down_revision = "20260916_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("daily_feedback_completed_on", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "daily_feedback_completed_on")
