"""phase 2 asset groups and image variants"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_0010"
down_revision = "20260715_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("primary_image_id", sa.String(36), nullable=True),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="approved"),
        sa.Column("publish_status", sa.String(20), nullable=False, server_default="published"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("title", "primary_image_id", "approval_status", "publish_status", "updated_at"):
        op.create_index(f"ix_asset_groups_{name}", "asset_groups", [name])

    with op.batch_alter_table("images") as batch:
        batch.add_column(sa.Column("asset_group_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("asset_role", sa.String(20), nullable=False, server_default="primary"))
        batch.add_column(sa.Column("width", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("height", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("aspect_ratio", sa.Float(), nullable=True))
        batch.add_column(sa.Column("channel", sa.String(100), nullable=True))
        batch.add_column(sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_foreign_key("fk_images_asset_group_id", "asset_groups", ["asset_group_id"], ["id"], ondelete="CASCADE")
        for name in ("asset_group_id", "asset_role", "channel", "is_current"):
            batch.create_index(f"ix_images_{name}", [name])

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO asset_groups "
            "(id, title, primary_image_id, approval_status, publish_status, created_by, created_at, updated_at) "
            "SELECT id, title, id, 'approved', 'published', uploader, created_at, created_at FROM images"
        )
    )
    bind.execute(sa.text("UPDATE images SET asset_group_id = id"))


def downgrade() -> None:
    with op.batch_alter_table("images") as batch:
        for name in ("is_current", "channel", "asset_role", "asset_group_id"):
            batch.drop_index(f"ix_images_{name}")
        batch.drop_constraint("fk_images_asset_group_id", type_="foreignkey")
        for name in ("is_current", "version_no", "channel", "aspect_ratio", "height", "width", "asset_role", "asset_group_id"):
            batch.drop_column(name)
    op.drop_table("asset_groups")
