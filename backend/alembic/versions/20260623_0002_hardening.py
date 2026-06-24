"""security hardening, sibling tag uniqueness, thumbnails and recycle bin"""

from alembic import op
import sqlalchemy as sa


revision = "20260623_0002"
down_revision = "20260623_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "tags",
            recreate="always",
            naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
        ) as batch:
            batch.drop_constraint("uq_tags_name", type_="unique")
    else:
        inspector = sa.inspect(bind)
        for constraint in inspector.get_unique_constraints("tags"):
            if constraint.get("column_names") == ["name"] and constraint.get("name"):
                op.drop_constraint(constraint["name"], "tags", type_="unique")
    op.drop_index("ix_tags_name", table_name="tags")
    op.create_index("ix_tags_name", "tags", ["name"], unique=False)
    op.create_index(
        "uq_tags_root_name",
        "tags",
        ["name"],
        unique=True,
        sqlite_where=sa.text("parent_id IS NULL"),
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_tags_parent_name",
        "tags",
        ["parent_id", "name"],
        unique=True,
        sqlite_where=sa.text("parent_id IS NOT NULL"),
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )

    with op.batch_alter_table("images") as batch:
        batch.add_column(sa.Column("thumbnail_storage_key", sa.String(500), nullable=True))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_unique_constraint(
            "uq_images_thumbnail_storage_key",
            ["thumbnail_storage_key"],
        )
        batch.create_index("ix_images_deleted_at", ["deleted_at"])

    op.create_table(
        "login_throttles",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_target_type", "audit_logs", ["target_type"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("login_throttles")
    with op.batch_alter_table("images") as batch:
        batch.drop_index("ix_images_deleted_at")
        batch.drop_constraint("uq_images_thumbnail_storage_key", type_="unique")
        batch.drop_column("deleted_at")
        batch.drop_column("thumbnail_storage_key")
    op.drop_index("uq_tags_parent_name", table_name="tags")
    op.drop_index("uq_tags_root_name", table_name="tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)
    with op.batch_alter_table("tags") as batch:
        batch.create_unique_constraint("uq_tags_name", ["name"])
