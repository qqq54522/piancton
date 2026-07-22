"""add primary proof and evidence facets to asset groups"""

import sqlalchemy as sa

from alembic import op

revision = "20260721_0019"
down_revision = "20260718_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("asset_groups") as batch:
        batch.add_column(
            sa.Column("primary_proof_point_code", sa.String(120), nullable=True)
        )
        batch.add_column(
            sa.Column("primary_evidence_point_code", sa.String(140), nullable=True)
        )
        batch.create_index(
            "ix_asset_groups_primary_proof_point_code",
            ["primary_proof_point_code"],
        )
        batch.create_index(
            "ix_asset_groups_primary_evidence_point_code",
            ["primary_evidence_point_code"],
        )


def downgrade() -> None:
    with op.batch_alter_table("asset_groups") as batch:
        batch.drop_index("ix_asset_groups_primary_evidence_point_code")
        batch.drop_index("ix_asset_groups_primary_proof_point_code")
        batch.drop_column("primary_evidence_point_code")
        batch.drop_column("primary_proof_point_code")
