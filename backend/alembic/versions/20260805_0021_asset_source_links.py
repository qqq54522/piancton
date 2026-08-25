"""add source links to asset groups"""

import sqlalchemy as sa

from alembic import op

revision = "20260805_0021"
down_revision = "20260728_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_source_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("asset_group_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("link_type", sa.String(length=40), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_group_id"],
            ["asset_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_asset_source_links_asset_group_id",
        "asset_source_links",
        ["asset_group_id"],
    )
    op.create_index(
        "ix_asset_source_links_link_type",
        "asset_source_links",
        ["link_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_asset_source_links_link_type", table_name="asset_source_links")
    op.drop_index("ix_asset_source_links_asset_group_id", table_name="asset_source_links")
    op.drop_table("asset_source_links")
