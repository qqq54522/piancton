"""add user private asset agent sessions"""

import sqlalchemy as sa

from alembic import op

revision = "20260825_0024"
down_revision = "20260825_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_agent_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("context_images_json", sa.Text(), nullable=False),
        sa.Column("suggested_questions_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_agent_sessions_user_id", "asset_agent_sessions", ["user_id"])
    op.create_index(
        "ix_asset_agent_sessions_expires_at",
        "asset_agent_sessions",
        ["expires_at"],
    )
    op.create_index(
        "ix_asset_agent_sessions_updated_at",
        "asset_agent_sessions",
        ["updated_at"],
    )
    op.create_index(
        "ix_asset_agent_sessions_user_updated",
        "asset_agent_sessions",
        ["user_id", "updated_at"],
    )

    op.create_table(
        "asset_agent_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("used_model", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["asset_agent_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_agent_messages_session_id", "asset_agent_messages", ["session_id"])
    op.create_index("ix_asset_agent_messages_role", "asset_agent_messages", ["role"])
    op.create_index(
        "ix_asset_agent_messages_created_at",
        "asset_agent_messages",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_asset_agent_messages_created_at", table_name="asset_agent_messages")
    op.drop_index("ix_asset_agent_messages_role", table_name="asset_agent_messages")
    op.drop_index("ix_asset_agent_messages_session_id", table_name="asset_agent_messages")
    op.drop_table("asset_agent_messages")
    op.drop_index("ix_asset_agent_sessions_user_updated", table_name="asset_agent_sessions")
    op.drop_index("ix_asset_agent_sessions_updated_at", table_name="asset_agent_sessions")
    op.drop_index("ix_asset_agent_sessions_expires_at", table_name="asset_agent_sessions")
    op.drop_index("ix_asset_agent_sessions_user_id", table_name="asset_agent_sessions")
    op.drop_table("asset_agent_sessions")
