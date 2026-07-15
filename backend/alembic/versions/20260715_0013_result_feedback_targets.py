"""phase 5 result-level search feedback targets"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_0013"
down_revision = "20260715_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("search_feedback_events") as batch:
        batch.add_column(sa.Column("result_image_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("asset_group_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_search_feedback_result_image",
            "images",
            ["result_image_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_search_feedback_asset_group",
            "asset_groups",
            ["asset_group_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_search_feedback_events_result_image_id",
            ["result_image_id"],
        )
        batch.create_index(
            "ix_search_feedback_events_asset_group_id",
            ["asset_group_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("search_feedback_events") as batch:
        batch.drop_index("ix_search_feedback_events_asset_group_id")
        batch.drop_index("ix_search_feedback_events_result_image_id")
        batch.drop_constraint("fk_search_feedback_asset_group", type_="foreignkey")
        batch.drop_constraint("fk_search_feedback_result_image", type_="foreignkey")
        batch.drop_column("asset_group_id")
        batch.drop_column("result_image_id")
