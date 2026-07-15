"""phase 6 remove legacy image semantics and requested search mode"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_0014"
down_revision = "20260715_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("search_logs") as batch:
        batch.drop_index("ix_search_logs_requested_mode")
        batch.drop_index("ix_search_logs_matched_category")
        batch.drop_column("requested_mode")
        batch.alter_column("matched_category", new_column_name="matched_concept")
    op.create_index(
        "ix_search_logs_matched_concept",
        "search_logs",
        ["matched_concept"],
    )

    op.drop_table("image_business_labels")
    op.drop_table("image_level2_categories")
    op.drop_table("image_categories")
    op.drop_table("image_tags")
    op.execute(sa.text("DELETE FROM tags WHERE node_type != 'system'"))


def downgrade() -> None:
    op.create_table(
        "image_tags",
        sa.Column(
            "image_id",
            sa.String(36),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.String(36),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "image_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "image_id",
            sa.String(36),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.UniqueConstraint("image_id", "name"),
    )
    op.create_index("ix_image_categories_image_id", "image_categories", ["image_id"])
    op.create_index("ix_image_categories_name", "image_categories", ["name"])

    op.create_table(
        "image_level2_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "image_id",
            sa.String(36),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category_name", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_image_level2_categories_image_id",
        "image_level2_categories",
        ["image_id"],
    )
    op.create_index(
        "ix_image_level2_categories_category_name",
        "image_level2_categories",
        ["category_name"],
    )

    op.create_table(
        "image_business_labels",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "image_id",
            sa.String(36),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.String(36),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label_code", sa.String(100), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_level", sa.String(10), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "analysis_run_id",
            sa.String(36),
            sa.ForeignKey("analysis_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "image_id",
            "tag_id",
            "origin",
            "analysis_run_id",
            name="uq_image_business_label_source",
        ),
    )
    for name in (
        "image_id",
        "tag_id",
        "label_code",
        "origin",
        "role",
        "review_status",
        "analysis_run_id",
        "created_at",
    ):
        op.create_index(
            f"ix_image_business_labels_{name}",
            "image_business_labels",
            [name],
        )

    with op.batch_alter_table("search_logs") as batch:
        batch.drop_index("ix_search_logs_matched_concept")
        batch.alter_column("matched_concept", new_column_name="matched_category")
    op.create_index(
        "ix_search_logs_matched_category",
        "search_logs",
        ["matched_category"],
    )
    with op.batch_alter_table("search_logs") as batch:
        batch.add_column(
            sa.Column(
                "requested_mode",
                sa.String(20),
                nullable=False,
                server_default="configured",
            )
        )
        batch.create_index("ix_search_logs_requested_mode", ["requested_mode"])
