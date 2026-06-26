"""image semantic embeddings"""

from alembic import op
import sqlalchemy as sa


revision = "20260626_0005"
down_revision = "20260623_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_embeddings",
        sa.Column(
            "image_id",
            sa.String(36),
            sa.ForeignKey("images.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("document_text", sa.Text(), nullable=False),
        sa.Column("vector_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_image_embeddings_model_name", "image_embeddings", ["model_name"])
    op.create_index("ix_image_embeddings_content_hash", "image_embeddings", ["content_hash"])
    op.create_index("ix_image_embeddings_updated_at", "image_embeddings", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_image_embeddings_updated_at", table_name="image_embeddings")
    op.drop_index("ix_image_embeddings_content_hash", table_name="image_embeddings")
    op.drop_index("ix_image_embeddings_model_name", table_name="image_embeddings")
    op.drop_table("image_embeddings")
