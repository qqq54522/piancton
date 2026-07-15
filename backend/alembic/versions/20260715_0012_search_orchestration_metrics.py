"""phase 4 search orchestration diagnostics"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_0012"
down_revision = "20260715_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "search_logs",
        sa.Column("top_asset_group_ids_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column("search_logs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column(
        "search_logs",
        sa.Column("timed_out", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "search_logs",
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "search_logs",
        sa.Column("reranker_used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "search_logs",
        sa.Column("degraded_sources_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "search_logs",
        sa.Column("branch_status_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_search_logs_duration_ms", "search_logs", ["duration_ms"])
    op.create_index("ix_search_logs_timed_out", "search_logs", ["timed_out"])
    op.create_index("ix_search_logs_cache_hit", "search_logs", ["cache_hit"])
    op.create_index("ix_search_logs_reranker_used", "search_logs", ["reranker_used"])


def downgrade() -> None:
    op.drop_index("ix_search_logs_reranker_used", table_name="search_logs")
    op.drop_index("ix_search_logs_cache_hit", table_name="search_logs")
    op.drop_index("ix_search_logs_timed_out", table_name="search_logs")
    op.drop_index("ix_search_logs_duration_ms", table_name="search_logs")
    op.drop_column("search_logs", "branch_status_json")
    op.drop_column("search_logs", "degraded_sources_json")
    op.drop_column("search_logs", "reranker_used")
    op.drop_column("search_logs", "cache_hit")
    op.drop_column("search_logs", "timed_out")
    op.drop_column("search_logs", "duration_ms")
    op.drop_column("search_logs", "top_asset_group_ids_json")
