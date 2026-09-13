"""track account-level onboarding completion

Revision ID: 20260913_0039
Revises: 20260913_0038
Create Date: 2026-09-13 14:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260913_0039"
down_revision = "20260913_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE users SET onboarding_completed_at = CURRENT_TIMESTAMP "
            "WHERE onboarding_completed_at IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed_at")
