"""remember allocated image titles so numeric suffixes are never reused"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260718_0018"
down_revision = "20260718_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = op.create_table(
        "image_title_reservations",
        sa.Column("normalized_title", sa.String(length=255), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_image_title_reservations_created_at",
        "image_title_reservations",
        ["created_at"],
    )

    bind = op.get_bind()
    seen: set[str] = set()
    rows = []
    for title in bind.execute(sa.text("SELECT title FROM images")).scalars():
        cleaned = (title or "").strip()[:255]
        normalized = cleaned.casefold()
        if cleaned and normalized not in seen:
            seen.add(normalized)
            rows.append({"normalized_title": normalized, "title": cleaned})
    if rows:
        op.bulk_insert(table, rows)


def downgrade() -> None:
    op.drop_index(
        "ix_image_title_reservations_created_at",
        table_name="image_title_reservations",
    )
    op.drop_table("image_title_reservations")

