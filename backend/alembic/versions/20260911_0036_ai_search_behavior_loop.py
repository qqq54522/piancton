"""add AI Search behavior outbox and persistent Agent image cards

Revision ID: 20260911_0036
Revises: 20260909_0035
Create Date: 2026-09-11 23:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260911_0036"
down_revision = "20260909_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("asset_agent_messages") as batch:
        batch.add_column(
            sa.Column("context_cards_json", sa.Text(), nullable=False, server_default="[]")
        )

    op.create_table(
        "ai_search_behavior_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_event_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("event_timestamp", sa.BigInteger(), nullable=False),
        sa.Column("event_scene", sa.String(length=80), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_search_behavior_status_created",
        "ai_search_behavior_events",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_ai_search_behavior_user_time",
        "ai_search_behavior_events",
        ["user_id", "event_timestamp"],
    )
    op.create_index(
        "ix_ai_search_behavior_source_event_id",
        "ai_search_behavior_events",
        ["source_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_ai_search_behavior_user_id",
        "ai_search_behavior_events",
        ["user_id"],
    )
    op.create_index(
        "ix_ai_search_behavior_item_id",
        "ai_search_behavior_events",
        ["item_id"],
    )
    op.create_index(
        "ix_ai_search_behavior_event_type",
        "ai_search_behavior_events",
        ["event_type"],
    )
    op.create_index(
        "ix_ai_search_behavior_status",
        "ai_search_behavior_events",
        ["status"],
    )
    op.create_index(
        "ix_ai_search_behavior_created_at",
        "ai_search_behavior_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("ai_search_behavior_events")
    with op.batch_alter_table("asset_agent_messages") as batch:
        batch.drop_column("context_cards_json")
