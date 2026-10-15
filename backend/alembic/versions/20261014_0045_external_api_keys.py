"""add managed external API keys

Revision ID: 20261014_0045
Revises: 20261008_0044
"""

import sqlalchemy as sa

from alembic import op

revision = "20261014_0045"
down_revision = "20261008_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("secret_preview", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("secret_hash"),
    )
    op.create_index("ix_external_api_keys_name", "external_api_keys", ["name"])
    op.create_index("ix_external_api_keys_key_prefix", "external_api_keys", ["key_prefix"])
    op.create_index("ix_external_api_keys_status", "external_api_keys", ["status"])
    op.create_index("ix_external_api_keys_created_by", "external_api_keys", ["created_by"])
    op.create_index("ix_external_api_keys_last_used_at", "external_api_keys", ["last_used_at"])


def downgrade() -> None:
    op.drop_index("ix_external_api_keys_last_used_at", table_name="external_api_keys")
    op.drop_index("ix_external_api_keys_created_by", table_name="external_api_keys")
    op.drop_index("ix_external_api_keys_status", table_name="external_api_keys")
    op.drop_index("ix_external_api_keys_key_prefix", table_name="external_api_keys")
    op.drop_index("ix_external_api_keys_name", table_name="external_api_keys")
    op.drop_table("external_api_keys")
