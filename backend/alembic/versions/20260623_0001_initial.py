"""initial secure schema"""

from alembic import op
import sqlalchemy as sa


revision = "20260623_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(20), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("tags.id", ondelete="SET NULL")),
        sa.Column("is_secondary", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)
    op.create_index("ix_tags_parent_id", "tags", ["parent_id"])

    op.create_table(
        "images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploader", sa.String(100), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("image_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_images_title", "images", ["title"])
    op.create_index("ix_images_created_at", "images", ["created_at"])
    op.create_index("ix_images_download_count", "images", ["download_count"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(500), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    op.create_table(
        "image_tags",
        sa.Column("image_id", sa.String(36), sa.ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.String(36), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "image_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("image_id", sa.String(36), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.UniqueConstraint("image_id", "name"),
    )
    op.create_index("ix_image_categories_image_id", "image_categories", ["image_id"])
    op.create_index("ix_image_categories_name", "image_categories", ["name"])
    op.create_table(
        "content_tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("image_id", sa.String(36), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_name", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("dimension", sa.String(50)),
    )
    op.create_index("ix_content_tags_image_id", "content_tags", ["image_id"])
    op.create_index("ix_content_tags_tag_name", "content_tags", ["tag_name"])
    op.create_table(
        "image_level2_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("image_id", sa.String(36), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_name", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text()),
    )
    op.create_index("ix_image_level2_categories_image_id", "image_level2_categories", ["image_id"])
    op.create_index("ix_image_level2_categories_category_name", "image_level2_categories", ["category_name"])
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_table("user_sessions")
    op.drop_table("image_level2_categories")
    op.drop_table("content_tags")
    op.drop_table("image_categories")
    op.drop_table("image_tags")
    op.drop_table("users")
    op.drop_table("images")
    op.drop_table("tags")
