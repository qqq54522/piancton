"""add manual recommendation copy to business concepts"""

import sqlalchemy as sa

from alembic import op

revision = "20260728_0020"
down_revision = "20260721_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("business_concepts") as batch:
        batch.add_column(sa.Column("recommendation_text", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("business_concepts") as batch:
        batch.drop_column("recommendation_text")
