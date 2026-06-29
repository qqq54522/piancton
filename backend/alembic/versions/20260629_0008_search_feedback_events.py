"""search feedback events"""

from alembic import op
import sqlalchemy as sa


revision = "20260629_0008"
down_revision = "20260629_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_feedback_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "search_log_id",
            sa.String(36),
            sa.ForeignKey("search_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("feedback_type", sa.String(40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_feedback_events_search_log_id", "search_feedback_events", ["search_log_id"])
    op.create_index("ix_search_feedback_events_actor_user_id", "search_feedback_events", ["actor_user_id"])
    op.create_index("ix_search_feedback_events_keyword", "search_feedback_events", ["keyword"])
    op.create_index("ix_search_feedback_events_feedback_type", "search_feedback_events", ["feedback_type"])
    op.create_index("ix_search_feedback_events_request_id", "search_feedback_events", ["request_id"])
    op.create_index("ix_search_feedback_events_created_at", "search_feedback_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_search_feedback_events_created_at", table_name="search_feedback_events")
    op.drop_index("ix_search_feedback_events_request_id", table_name="search_feedback_events")
    op.drop_index("ix_search_feedback_events_feedback_type", table_name="search_feedback_events")
    op.drop_index("ix_search_feedback_events_keyword", table_name="search_feedback_events")
    op.drop_index("ix_search_feedback_events_actor_user_id", table_name="search_feedback_events")
    op.drop_index("ix_search_feedback_events_search_log_id", table_name="search_feedback_events")
    op.drop_table("search_feedback_events")
