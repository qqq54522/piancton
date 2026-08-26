"""add usage analytics events and api center settings"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260826_0026"
down_revision = "20260825_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_center_settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "user_usage_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("path", sa.String(length=300), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_usage_events_user_created", "user_usage_events", ["user_id", "created_at"])
    op.create_index("ix_user_usage_events_event_created", "user_usage_events", ["event_type", "created_at"])
    op.create_index("ix_user_usage_events_created_at", "user_usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_usage_events_created_at", table_name="user_usage_events")
    op.drop_index("ix_user_usage_events_event_created", table_name="user_usage_events")
    op.drop_index("ix_user_usage_events_user_created", table_name="user_usage_events")
    op.drop_table("user_usage_events")
    op.drop_table("api_center_settings")
