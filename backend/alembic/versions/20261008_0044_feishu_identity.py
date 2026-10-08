"""Store Feishu identity and department snapshots on local users.

Revision ID: 20261008_0044
Revises: 20260916_0043
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261008_0044"
down_revision = "20260916_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("feishu_open_id", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("feishu_union_id", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("feishu_user_id", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("feishu_tenant_key", sa.String(128), nullable=True))
    op.add_column("users", sa.Column("feishu_display_name", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("feishu_department_names", sa.String(1000), nullable=True))
    op.add_column(
        "users",
        sa.Column("last_feishu_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_feishu_open_id", "users", ["feishu_open_id"], unique=True)
    op.create_index("ix_users_feishu_union_id", "users", ["feishu_union_id"], unique=False)
    op.create_index("ix_users_feishu_user_id", "users", ["feishu_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_feishu_user_id", table_name="users")
    op.drop_index("ix_users_feishu_union_id", table_name="users")
    op.drop_index("ix_users_feishu_open_id", table_name="users")
    op.drop_column("users", "last_feishu_login_at")
    op.drop_column("users", "feishu_department_names")
    op.drop_column("users", "feishu_display_name")
    op.drop_column("users", "feishu_tenant_key")
    op.drop_column("users", "feishu_user_id")
    op.drop_column("users", "feishu_union_id")
    op.drop_column("users", "feishu_open_id")
