"""analysis runs and image business label sources"""

from alembic import op
import sqlalchemy as sa


revision = "20260623_0004"
down_revision = "20260623_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("image_id", sa.String(36), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("taxonomy_version", sa.String(30), nullable=True),
        sa.Column("model_provider", sa.String(100), nullable=True),
        sa.Column("model_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analysis_runs_image_id", "analysis_runs", ["image_id"])
    op.create_index("ix_analysis_runs_task", "analysis_runs", ["task"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])
    op.create_index("ix_analysis_runs_created_at", "analysis_runs", ["created_at"])

    op.create_table(
        "image_business_labels",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("image_id", sa.String(36), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.String(36), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label_code", sa.String(100), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_level", sa.String(10), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("analysis_run_id", sa.String(36), sa.ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "image_id",
            "tag_id",
            "origin",
            "analysis_run_id",
            name="uq_image_business_label_source",
        ),
    )
    op.create_index("ix_image_business_labels_image_id", "image_business_labels", ["image_id"])
    op.create_index("ix_image_business_labels_tag_id", "image_business_labels", ["tag_id"])
    op.create_index("ix_image_business_labels_label_code", "image_business_labels", ["label_code"])
    op.create_index("ix_image_business_labels_origin", "image_business_labels", ["origin"])
    op.create_index("ix_image_business_labels_role", "image_business_labels", ["role"])
    op.create_index("ix_image_business_labels_review_status", "image_business_labels", ["review_status"])
    op.create_index("ix_image_business_labels_analysis_run_id", "image_business_labels", ["analysis_run_id"])
    op.create_index("ix_image_business_labels_created_at", "image_business_labels", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_image_business_labels_created_at", table_name="image_business_labels")
    op.drop_index("ix_image_business_labels_analysis_run_id", table_name="image_business_labels")
    op.drop_index("ix_image_business_labels_review_status", table_name="image_business_labels")
    op.drop_index("ix_image_business_labels_role", table_name="image_business_labels")
    op.drop_index("ix_image_business_labels_origin", table_name="image_business_labels")
    op.drop_index("ix_image_business_labels_label_code", table_name="image_business_labels")
    op.drop_index("ix_image_business_labels_tag_id", table_name="image_business_labels")
    op.drop_index("ix_image_business_labels_image_id", table_name="image_business_labels")
    op.drop_table("image_business_labels")
    op.drop_index("ix_analysis_runs_created_at", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_status", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_task", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_image_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
