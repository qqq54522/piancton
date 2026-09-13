"""add announcements and account read cursor

Revision ID: 20260913_0040
Revises: 20260913_0039
Create Date: 2026-09-13 22:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260913_0040"
down_revision = "20260913_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("announcements_read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE users SET announcements_read_at = CURRENT_TIMESTAMP "
            "WHERE announcements_read_at IS NULL"
        )
    )
    op.create_table(
        "announcements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("published_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_announcements_published_at_id",
        "announcements",
        ["published_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_announcements_published_at",
        "announcements",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        "ix_announcements_published_by_user_id",
        "announcements",
        ["published_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_announcements_published_by_user_id", table_name="announcements")
    op.drop_index("ix_announcements_published_at", table_name="announcements")
    op.drop_index("ix_announcements_published_at_id", table_name="announcements")
    op.drop_table("announcements")
    op.drop_column("users", "announcements_read_at")
