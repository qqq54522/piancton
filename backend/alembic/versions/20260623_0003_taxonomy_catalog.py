"""versioned taxonomy catalog and assignable tag nodes"""

from alembic import op
import sqlalchemy as sa


revision = "20260623_0003"
down_revision = "20260623_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tags") as batch:
        batch.add_column(sa.Column("code", sa.String(100), nullable=True))
        batch.add_column(
            sa.Column("node_type", sa.String(30), nullable=False, server_default="custom")
        )
        batch.add_column(
            sa.Column("assignable", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column("status", sa.String(20), nullable=False, server_default="active")
        )
        batch.add_column(sa.Column("taxonomy_version", sa.String(30), nullable=True))
        batch.add_column(
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_index("ix_tags_code", ["code"], unique=True)
        batch.create_index("ix_tags_node_type", ["node_type"])
        batch.create_index("ix_tags_assignable", ["assignable"])
        batch.create_index("ix_tags_status", ["status"])


def downgrade() -> None:
    with op.batch_alter_table("tags") as batch:
        batch.drop_index("ix_tags_status")
        batch.drop_index("ix_tags_assignable")
        batch.drop_index("ix_tags_node_type")
        batch.drop_index("ix_tags_code")
        batch.drop_column("sort_order")
        batch.drop_column("taxonomy_version")
        batch.drop_column("status")
        batch.drop_column("assignable")
        batch.drop_column("node_type")
        batch.drop_column("code")
