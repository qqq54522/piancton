"""phase 1 versioned business concepts"""

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "20260715_0009"
down_revision = "20260629_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_concepts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("concept_type", sa.String(50), nullable=False, server_default="business_term"),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "replaced_by_concept_id",
            sa.String(36),
            sa.ForeignKey("business_concepts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    for name in ("code", "name", "concept_type", "status", "replaced_by_concept_id", "updated_at"):
        op.create_index(f"ix_business_concepts_{name}", "business_concepts", [name])

    op.create_table(
        "concept_system_links",
        sa.Column("concept_id", sa.String(36), sa.ForeignKey("business_concepts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("system_tag_id", sa.String(36), sa.ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="core"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.create_index("ix_concept_system_links_role", "concept_system_links", ["role"])
    op.create_index("ix_concept_system_links_status", "concept_system_links", ["status"])

    op.create_table(
        "concept_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_concept_id", sa.String(36), sa.ForeignKey("business_concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_concept_id", sa.String(36), sa.ForeignKey("business_concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.UniqueConstraint("source_concept_id", "target_concept_id", "relation_type", name="uq_concept_relation"),
    )
    for name in ("source_concept_id", "target_concept_id", "relation_type", "status"):
        op.create_index(f"ix_concept_relations_{name}", "concept_relations", [name])

    op.create_table(
        "concept_search_phrases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("concept_id", sa.String(36), sa.ForeignKey("business_concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phrase", sa.String(300), nullable=False),
        sa.Column("phrase_type", sa.String(30), nullable=False, server_default="official"),
        sa.Column("origin", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="accepted"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("source_ref", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("concept_id", "phrase", "origin", name="uq_concept_phrase_origin"),
    )
    for name in ("concept_id", "phrase", "phrase_type", "origin", "review_status"):
        op.create_index(f"ix_concept_search_phrases_{name}", "concept_search_phrases", [name])

    _backfill_tag_concepts()


def _backfill_tag_concepts() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    rows = bind.execute(
        sa.text(
            "SELECT id, code, name, parent_id FROM tags "
            "WHERE node_type = 'image_label' AND code IS NOT NULL"
        )
    ).mappings()
    for row in rows:
        concept_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO business_concepts "
                "(id, code, name, concept_type, status, version, created_at, updated_at) "
                "VALUES (:id, :code, :name, 'business_term', 'active', 1, :now, :now)"
            ),
            {"id": concept_id, "code": row["code"], "name": row["name"], "now": now},
        )
        if row["parent_id"]:
            bind.execute(
                sa.text(
                    "INSERT INTO concept_system_links "
                    "(concept_id, system_tag_id, role, weight, status) "
                    "VALUES (:concept_id, :system_tag_id, 'core', 1, 'active')"
                ),
                {"concept_id": concept_id, "system_tag_id": row["parent_id"]},
            )
        bind.execute(
            sa.text(
                "INSERT INTO concept_search_phrases "
                "(id, concept_id, phrase, phrase_type, origin, review_status, weight, created_at) "
                "VALUES (:id, :concept_id, :phrase, 'official', 'migrated', 'accepted', 1, :now)"
            ),
            {"id": str(uuid.uuid4()), "concept_id": concept_id, "phrase": row["name"], "now": now},
        )


def downgrade() -> None:
    op.drop_table("concept_search_phrases")
    op.drop_table("concept_relations")
    op.drop_table("concept_system_links")
    op.drop_table("business_concepts")
