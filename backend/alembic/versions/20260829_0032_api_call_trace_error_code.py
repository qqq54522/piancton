"""add api call trace error code

Revision ID: 20260829_0032
Revises: 20260829_0031
Create Date: 2026-08-29 00:32:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260829_0032"
down_revision = "20260829_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_call_traces",
        sa.Column("error_code", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "ix_model_call_traces_error_code",
        "model_call_traces",
        ["error_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_model_call_traces_error_code", table_name="model_call_traces")
    op.drop_column("model_call_traces", "error_code")
