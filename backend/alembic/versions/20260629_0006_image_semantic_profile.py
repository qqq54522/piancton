"""image semantic profile"""

from alembic import op
import sqlalchemy as sa


revision = "20260629_0006"
down_revision = "20260626_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("images", sa.Column("semantic_profile_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("images", "semantic_profile_json")
