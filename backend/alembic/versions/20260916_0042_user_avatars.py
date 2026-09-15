"""Private account avatars and registration presets.

Revision ID: 20260916_0042
Revises: 20260915_0041
"""

import sqlalchemy as sa
from alembic import op

revision = "20260916_0042"
down_revision = "20260915_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_preset_id", sa.String(24), nullable=True))
    op.add_column("users", sa.Column("avatar_storage_key", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("avatar_thumbnail_key", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar_thumbnail_key")
    op.drop_column("users", "avatar_storage_key")
    op.drop_column("users", "avatar_preset_id")
