"""search analytics logs"""

from alembic import op
import sqlalchemy as sa


revision = "20260629_0007"
down_revision = "20260629_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("requested_mode", sa.String(20), nullable=False),
        sa.Column("served_mode", sa.String(20), nullable=False),
        sa.Column("fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("normalized_query", sa.String(200), nullable=True),
        sa.Column("query_type", sa.String(80), nullable=True),
        sa.Column("matched_category", sa.String(200), nullable=True),
        sa.Column("top_image_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("match_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_logs_actor_user_id", "search_logs", ["actor_user_id"])
    op.create_index("ix_search_logs_keyword", "search_logs", ["keyword"])
    op.create_index("ix_search_logs_requested_mode", "search_logs", ["requested_mode"])
    op.create_index("ix_search_logs_served_mode", "search_logs", ["served_mode"])
    op.create_index("ix_search_logs_fallback", "search_logs", ["fallback"])
    op.create_index("ix_search_logs_result_count", "search_logs", ["result_count"])
    op.create_index("ix_search_logs_normalized_query", "search_logs", ["normalized_query"])
    op.create_index("ix_search_logs_query_type", "search_logs", ["query_type"])
    op.create_index("ix_search_logs_matched_category", "search_logs", ["matched_category"])
    op.create_index("ix_search_logs_request_id", "search_logs", ["request_id"])
    op.create_index("ix_search_logs_created_at", "search_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_search_logs_created_at", table_name="search_logs")
    op.drop_index("ix_search_logs_request_id", table_name="search_logs")
    op.drop_index("ix_search_logs_matched_category", table_name="search_logs")
    op.drop_index("ix_search_logs_query_type", table_name="search_logs")
    op.drop_index("ix_search_logs_normalized_query", table_name="search_logs")
    op.drop_index("ix_search_logs_result_count", table_name="search_logs")
    op.drop_index("ix_search_logs_fallback", table_name="search_logs")
    op.drop_index("ix_search_logs_served_mode", table_name="search_logs")
    op.drop_index("ix_search_logs_requested_mode", table_name="search_logs")
    op.drop_index("ix_search_logs_keyword", table_name="search_logs")
    op.drop_index("ix_search_logs_actor_user_id", table_name="search_logs")
    op.drop_table("search_logs")
