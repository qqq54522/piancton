"""release image titles when images enter the trash

Revision ID: 20260909_0034
Revises: 20260829_0033
Create Date: 2026-09-09 00:34:00.000000
"""

from __future__ import annotations

import re

import sqlalchemy as sa

from alembic import op

revision = "20260909_0034"
down_revision = "20260829_0033"
branch_labels = None
depends_on = None

MAX_TITLE_LENGTH = 255
SEQUENCE_PATTERN = re.compile(r"^(.*?)(\d{3})$")


def upgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_images_title_normalized"))
    op.create_index(
        "uq_images_title_normalized",
        "images",
        [sa.text("lower(trim(title))")],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.execute(
        sa.text("DROP INDEX IF EXISTS ix_image_title_reservations_created_at")
    )
    op.drop_table("image_title_reservations")


def downgrade() -> None:
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
    rows = list(
        bind.execute(
            sa.text(
                "SELECT id, title FROM images "
                "ORDER BY CASE WHEN deleted_at IS NULL THEN 0 ELSE 1 END, created_at, id"
            )
        ).mappings()
    )
    occupied: set[str] = set()
    resolved_titles: list[str] = []
    reservations: list[dict[str, str]] = []
    for row in rows:
        requested = _clean(row["title"] or "素材") or "素材"
        resolved = _allocate(requested, occupied, resolved_titles)
        if resolved != row["title"]:
            bind.execute(
                sa.text("UPDATE images SET title = :title WHERE id = :image_id"),
                {"title": resolved, "image_id": row["id"]},
            )
            bind.execute(
                sa.text(
                    "UPDATE asset_groups SET title = :title "
                    "WHERE primary_image_id = :image_id"
                ),
                {"title": resolved, "image_id": row["id"]},
            )
        occupied.add(resolved.casefold())
        resolved_titles.append(resolved)
        reservations.append(
            {"normalized_title": resolved.casefold(), "title": resolved}
        )

    if reservations:
        op.bulk_insert(table, reservations)
    op.execute(sa.text("DROP INDEX IF EXISTS uq_images_title_normalized"))
    op.create_index(
        "uq_images_title_normalized",
        "images",
        [sa.text("lower(trim(title))")],
        unique=True,
    )


def _clean(value: str) -> str:
    return value.strip()[:MAX_TITLE_LENGTH]


def _allocate(requested: str, occupied: set[str], existing: list[str]) -> str:
    title = _clean(requested)
    if title.casefold() not in occupied:
        return title
    match = SEQUENCE_PATTERN.fullmatch(title)
    possible_base = match.group(1) if match and match.group(1) else title
    base = (
        possible_base
        if possible_base != title and possible_base.casefold() in occupied
        else title
    )
    highest = 0
    for item in existing:
        candidate = _clean(item)
        candidate_match = SEQUENCE_PATTERN.fullmatch(candidate)
        if candidate.casefold() == base.casefold():
            highest = max(highest, 0)
        elif candidate_match and candidate_match.group(1).casefold() == base.casefold():
            highest = max(highest, int(candidate_match.group(2)))
    sequence = highest + 1
    while True:
        suffix = f"{sequence:03d}"
        resolved = f"{base[: MAX_TITLE_LENGTH - len(suffix)]}{suffix}"
        if resolved.casefold() not in occupied:
            return resolved
        sequence += 1
