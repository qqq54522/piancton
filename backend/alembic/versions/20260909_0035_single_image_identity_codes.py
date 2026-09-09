"""replace permanent asset/version ledger with one active-image identity

Revision ID: 20260909_0035
Revises: 20260909_0034
Create Date: 2026-09-09 03:35:00.000000
"""

from __future__ import annotations

import hashlib

import sqlalchemy as sa

from alembic import op

revision = "20260909_0035"
down_revision = "20260909_0034"
branch_labels = None
depends_on = None

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _short_code(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big")
    chars: list[str] = []
    for _ in range(6):
        value, remainder = divmod(value, len(CODE_ALPHABET))
        chars.append(CODE_ALPHABET[remainder])
    return "PC-" + "".join(chars)


def _unique_code(seed: str, used: set[str], preferred: str | None = None) -> str:
    suffix = 0
    code = preferred or _short_code(seed)
    while code in used:
        suffix += 1
        code = _short_code(f"{seed}:{suffix}")
    used.add(code)
    return code


def upgrade() -> None:
    with op.batch_alter_table("images") as batch:
        batch.add_column(sa.Column("identity_code", sa.String(length=32), nullable=True))
        batch.create_index("ix_images_identity_code", ["identity_code"], unique=True)

    bind = op.get_bind()
    rows = list(
        bind.execute(
            sa.text(
                "SELECT i.id, i.deleted_at, g.asset_code, g.primary_image_id "
                "FROM images i LEFT JOIN asset_groups g ON g.id = i.asset_group_id "
                "ORDER BY i.created_at, i.id"
            )
        ).mappings()
    )
    used: set[str] = set()
    for row in rows:
        if row["deleted_at"] is not None:
            continue
        preferred = (
            str(row["asset_code"])
            if row["asset_code"] and row["primary_image_id"] == row["id"]
            else None
        )
        code = _unique_code(str(row["id"]), used, preferred)
        bind.execute(
            sa.text("UPDATE images SET identity_code = :code WHERE id = :image_id"),
            {"code": code, "image_id": row["id"]},
        )

    op.drop_index("ix_asset_identity_codes_image_id", table_name="asset_identity_codes")
    op.drop_index("ix_asset_identity_codes_asset_group_id", table_name="asset_identity_codes")
    op.drop_index("ix_asset_identity_codes_code_type", table_name="asset_identity_codes")
    op.drop_table("asset_identity_codes")
    with op.batch_alter_table("images") as batch:
        batch.drop_index("ix_images_version_code")
        batch.drop_column("version_code")
    with op.batch_alter_table("asset_groups") as batch:
        batch.drop_index("ix_asset_groups_asset_code")
        batch.drop_column("asset_code")


def downgrade() -> None:
    with op.batch_alter_table("asset_groups") as batch:
        batch.add_column(sa.Column("asset_code", sa.String(length=32), nullable=True))
        batch.create_index("ix_asset_groups_asset_code", ["asset_code"], unique=True)
    with op.batch_alter_table("images") as batch:
        batch.add_column(sa.Column("version_code", sa.String(length=32), nullable=True))
        batch.create_index("ix_images_version_code", ["version_code"], unique=True)

    op.create_table(
        "asset_identity_codes",
        sa.Column("code", sa.String(length=32), primary_key=True),
        sa.Column("code_type", sa.String(length=20), nullable=False),
        sa.Column("asset_group_id", sa.String(length=36), nullable=True),
        sa.Column("image_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["asset_group_id"], ["asset_groups.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_asset_identity_codes_code_type", "asset_identity_codes", ["code_type"]
    )
    op.create_index(
        "ix_asset_identity_codes_asset_group_id",
        "asset_identity_codes",
        ["asset_group_id"],
    )
    op.create_index(
        "ix_asset_identity_codes_image_id", "asset_identity_codes", ["image_id"]
    )

    bind = op.get_bind()
    groups = list(
        bind.execute(
            sa.text("SELECT id FROM asset_groups ORDER BY created_at, id")
        ).mappings()
    )
    used: set[str] = set()
    group_codes: dict[str, str] = {}
    for row in groups:
        group_id = str(row["id"])
        code = _unique_code(group_id, used)
        group_codes[group_id] = code
        bind.execute(
            sa.text("UPDATE asset_groups SET asset_code = :code WHERE id = :group_id"),
            {"code": code, "group_id": group_id},
        )
        bind.execute(
            sa.text(
                "INSERT INTO asset_identity_codes "
                "(code, code_type, asset_group_id, created_at) "
                "VALUES (:code, 'asset', :group_id, CURRENT_TIMESTAMP)"
            ),
            {"code": code, "group_id": group_id},
        )

    images = list(
        bind.execute(
            sa.text(
                "SELECT id, asset_group_id, version_no FROM images "
                "ORDER BY asset_group_id, version_no, created_at, id"
            )
        ).mappings()
    )
    version_counts: dict[str, int] = {}
    for row in images:
        group_id = str(row["asset_group_id"])
        asset_code = group_codes[group_id]
        version_no = int(row["version_no"] or 1)
        version_counts[group_id] = max(version_counts.get(group_id, 0), version_no)
        code = f"{asset_code}-V{version_no:02d}"
        while code in used:
            version_counts[group_id] += 1
            code = f"{asset_code}-V{version_counts[group_id]:02d}"
        used.add(code)
        bind.execute(
            sa.text("UPDATE images SET version_code = :code WHERE id = :image_id"),
            {"code": code, "image_id": row["id"]},
        )
        bind.execute(
            sa.text(
                "INSERT INTO asset_identity_codes "
                "(code, code_type, asset_group_id, image_id, created_at) "
                "VALUES (:code, 'version', :group_id, :image_id, CURRENT_TIMESTAMP)"
            ),
            {
                "code": code,
                "group_id": row["asset_group_id"],
                "image_id": row["id"],
            },
        )

    with op.batch_alter_table("asset_groups") as batch:
        batch.alter_column("asset_code", existing_type=sa.String(length=32), nullable=False)
    with op.batch_alter_table("images") as batch:
        batch.alter_column("version_code", existing_type=sa.String(length=32), nullable=False)
        batch.drop_index("ix_images_identity_code")
        batch.drop_column("identity_code")
