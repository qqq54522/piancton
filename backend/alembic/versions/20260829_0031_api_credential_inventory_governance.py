"""add api credential inventory governance"""

import sqlalchemy as sa

from alembic import op

revision = "20260829_0031"
down_revision = "20260828_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_api_credentials",
        sa.Column(
            "api_key_fingerprint",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.create_index(
        "ix_model_api_credentials_inventory_identity",
        "model_api_credentials",
        ["provider_type", "base_url", "model_name", "api_key_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_model_api_credentials_inventory_identity",
        table_name="model_api_credentials",
    )
    op.drop_column("model_api_credentials", "api_key_fingerprint")
