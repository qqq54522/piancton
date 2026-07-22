"""make user-defined image titles globally unique with stable numeric suffixes"""

from __future__ import annotations

import re

import sqlalchemy as sa

from alembic import op

revision = "20260718_0017"
down_revision = "20260717_0016"
branch_labels = None
depends_on = None


MAX_TITLE_LENGTH = 255
SEQUENCE_PATTERN = re.compile(r"^(.*?)(\d{3})$")


def _clean(value: str) -> str:
    return value.strip()[:MAX_TITLE_LENGTH]


def _namespace(value: str) -> str:
    title = _clean(value)
    match = SEQUENCE_PATTERN.fullmatch(title)
    return match.group(1) if match and match.group(1) else title


def _allocate(requested: str, occupied: set[str], existing: list[str]) -> str:
    title = _clean(requested)
    if title.casefold() not in occupied:
        return title

    possible_base = _namespace(title)
    base = (
        possible_base
        if possible_base != title
        and possible_base.casefold() in occupied
        else title
    )
    base_key = base.casefold()
    highest = 0
    for item in existing:
        candidate = _clean(item)
        match = SEQUENCE_PATTERN.fullmatch(candidate)
        if candidate.casefold() == base_key:
            highest = max(highest, 0)
        elif match and match.group(1).casefold() == base_key:
            highest = max(highest, int(match.group(2)))

    sequence = highest + 1
    while True:
        suffix = f"{sequence:03d}"
        resolved = f"{base[: MAX_TITLE_LENGTH - len(suffix)]}{suffix}"
        if resolved.casefold() not in occupied:
            return resolved
        sequence += 1


def upgrade() -> None:
    bind = op.get_bind()
    rows = list(
        bind.execute(
            sa.text(
                "SELECT id, title FROM images "
                "ORDER BY created_at ASC, id ASC"
            )
        ).mappings()
    )

    occupied: set[str] = set()
    resolved_titles: list[str] = []
    for row in rows:
        requested = _clean(row["title"] or "素材") or "素材"
        resolved = _allocate(requested, occupied, resolved_titles)
        occupied.add(resolved.casefold())
        resolved_titles.append(resolved)
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

    op.create_index(
        "uq_images_title_normalized",
        "images",
        [sa.text("lower(trim(title))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_images_title_normalized", table_name="images")
