"""add api health check error code

Revision ID: 20260829_0033
Revises: 20260829_0032
Create Date: 2026-08-29 00:33:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260829_0033"
down_revision = "20260829_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_api_health_checks",
        sa.Column("error_code", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "ix_model_api_health_checks_error_code",
        "model_api_health_checks",
        ["error_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_model_api_health_checks_error_code",
        table_name="model_api_health_checks",
    )
    op.drop_column("model_api_health_checks", "error_code")
