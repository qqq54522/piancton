"""add manual asset refinement metadata"""

import sqlalchemy as sa

from alembic import op

revision = "20260717_0015"
down_revision = "20260715_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("asset_groups") as batch:
        batch.add_column(sa.Column("style_label", sa.String(100), nullable=True))
        batch.add_column(sa.Column("is_scene_image", sa.Boolean(), nullable=True))
        batch.create_index("ix_asset_groups_style_label", ["style_label"])


def downgrade() -> None:
    with op.batch_alter_table("asset_groups") as batch:
        batch.drop_index("ix_asset_groups_style_label")
        batch.drop_column("is_scene_image")
        batch.drop_column("style_label")
