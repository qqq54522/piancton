"""channel-specific browse folders; preserve legacy image channels and business links

Revision ID: 20260915_0041
Revises: 20260913_0040
"""

import sqlalchemy as sa

from alembic import op

revision = "20260915_0041"
down_revision = "20260913_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managed_channels",
        sa.Column("name", sa.String(100), primary_key=True),
        sa.Column("first_level_label", sa.String(30), nullable=False, server_default="分类"),
        sa.Column("second_level_label", sa.String(30), nullable=False, server_default="子分类"),
        sa.Column("third_level_label", sa.String(30), nullable=False, server_default="细分"),
    )
    op.create_table(
        "channel_folders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "channel_name",
            sa.String(100),
            sa.ForeignKey("managed_channels.name", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.String(36),
            sa.ForeignKey("channel_folders.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("name", sa.String(80), nullable=False),
    )
    op.create_index("ix_channel_folders_channel_name", "channel_folders", ["channel_name"])
    op.create_index("ix_channel_folders_parent_id", "channel_folders", ["parent_id"])
    op.create_index(
        "ix_channel_folders_channel_parent", "channel_folders", ["channel_name", "parent_id"]
    )
    op.create_table(
        "image_channel_placements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "image_id",
            sa.String(36),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_name",
            sa.String(100),
            sa.ForeignKey("managed_channels.name", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "folder_id",
            sa.String(36),
            sa.ForeignKey("channel_folders.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("image_id", "channel_name", name="uq_image_channel_placement"),
    )
    op.create_index(
        "ix_image_channel_placements_image_id", "image_channel_placements", ["image_id"]
    )
    op.create_index(
        "ix_image_channel_placements_channel_name", "image_channel_placements", ["channel_name"]
    )
    op.create_index(
        "ix_image_channel_placements_folder_id", "image_channel_placements", ["folder_id"]
    )


def downgrade() -> None:
    op.drop_table("image_channel_placements")
    op.drop_table("channel_folders")
    op.drop_table("managed_channels")
