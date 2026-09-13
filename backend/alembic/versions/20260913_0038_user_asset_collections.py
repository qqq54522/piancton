"""add user likes and private asset collection boards

Revision ID: 20260913_0038
Revises: 20260912_0037
Create Date: 2026-09-13 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260913_0038"
down_revision = "20260912_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_asset_likes",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("asset_group_id", sa.String(length=36), nullable=False),
        sa.Column("preferred_image_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["asset_group_id"], ["asset_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["preferred_image_id"], ["images.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("user_id", "asset_group_id"),
    )
    op.create_index(
        "ix_user_asset_likes_user_created",
        "user_asset_likes",
        ["user_id", "created_at", "asset_group_id"],
    )
    op.create_index(
        "ix_user_asset_likes_created_at", "user_asset_likes", ["created_at"]
    )

    op.create_table(
        "asset_collection_boards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "normalized_name", name="uq_asset_board_user_name"),
    )
    op.create_index(
        "ix_asset_boards_user_updated",
        "asset_collection_boards",
        ["user_id", "updated_at", "id"],
    )
    op.create_index(
        "ix_asset_collection_boards_user_id",
        "asset_collection_boards",
        ["user_id"],
    )
    op.create_index(
        "ix_asset_collection_boards_updated_at",
        "asset_collection_boards",
        ["updated_at"],
    )

    op.create_table(
        "asset_collection_board_items",
        sa.Column("board_id", sa.String(length=36), nullable=False),
        sa.Column("asset_group_id", sa.String(length=36), nullable=False),
        sa.Column("preferred_image_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["board_id"], ["asset_collection_boards.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["asset_group_id"], ["asset_groups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["preferred_image_id"], ["images.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("board_id", "asset_group_id"),
    )
    op.create_index(
        "ix_asset_board_items_board_created",
        "asset_collection_board_items",
        ["board_id", "created_at", "asset_group_id"],
    )
    op.create_index(
        "ix_asset_board_items_asset_group",
        "asset_collection_board_items",
        ["asset_group_id"],
    )
    op.create_index(
        "ix_asset_collection_board_items_created_at",
        "asset_collection_board_items",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("asset_collection_board_items")
    op.drop_table("asset_collection_boards")
    op.drop_table("user_asset_likes")
