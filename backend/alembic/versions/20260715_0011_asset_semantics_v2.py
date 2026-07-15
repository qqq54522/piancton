"""phase 3 asset concept relations, phrases and semantic profile v2"""

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from alembic import op

revision = "20260715_0011"
down_revision = "20260715_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_concept_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "asset_group_id",
            sa.String(36),
            sa.ForeignKey("asset_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "concept_id",
            sa.String(36),
            sa.ForeignKey("business_concepts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("relation_role", sa.String(30), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_reason", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "asset_group_id",
            "concept_id",
            "origin",
            "relation_role",
            name="uq_asset_concept_source_role",
        ),
    )
    for name in ("asset_group_id", "concept_id", "relation_role", "origin", "review_status"):
        op.create_index(f"ix_asset_concept_links_{name}", "asset_concept_links", [name])

    op.create_table(
        "asset_search_phrases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "asset_group_id",
            sa.String(36),
            sa.ForeignKey("asset_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phrase", sa.String(300), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("asset_group_id", "phrase", "origin", name="uq_asset_phrase_origin"),
    )
    for name in ("asset_group_id", "phrase", "origin", "review_status"):
        op.create_index(f"ix_asset_search_phrases_{name}", "asset_search_phrases", [name])

    _backfill_relations_and_phrases()
    _upgrade_semantic_profiles()


def _backfill_relations_and_phrases() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    rows = bind.execute(
        sa.text(
            "SELECT i.asset_group_id, c.id AS concept_id, l.origin, l.role, "
            "l.review_status, l.confidence, l.reason, l.analysis_run_id "
            "FROM image_business_labels l "
            "JOIN images i ON i.id = l.image_id "
            "JOIN business_concepts c ON c.code = l.label_code "
            "WHERE i.asset_group_id IS NOT NULL"
        )
    ).mappings()
    seen = set()
    for row in rows:
        role = "expresses" if row["role"] == "primary" else "supports"
        key = (row["asset_group_id"], row["concept_id"], row["origin"], role)
        if key in seen:
            continue
        seen.add(key)
        bind.execute(
            sa.text(
                "INSERT INTO asset_concept_links "
                "(id, asset_group_id, concept_id, relation_role, origin, review_status, "
                "confidence, evidence_reason, source_ref, created_at) "
                "VALUES (:id, :asset_group_id, :concept_id, :role, :origin, "
                ":review_status, :confidence, :reason, :source_ref, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "asset_group_id": row["asset_group_id"],
                "concept_id": row["concept_id"],
                "role": role,
                "origin": row["origin"],
                "review_status": row["review_status"],
                "confidence": row["confidence"],
                "reason": row["reason"],
                "source_ref": row["analysis_run_id"],
                "now": now,
            },
        )

    phrases = bind.execute(
        sa.text(
            "SELECT DISTINCT i.asset_group_id, ct.tag_name FROM content_tags ct "
            "JOIN images i ON i.id = ct.image_id "
            "WHERE ct.dimension = '用户预期搜索词' AND i.asset_group_id IS NOT NULL"
        )
    ).mappings()
    for row in phrases:
        bind.execute(
            sa.text(
                "INSERT INTO asset_search_phrases "
                "(id, asset_group_id, phrase, origin, review_status, weight, created_at) "
                "VALUES (:id, :asset_group_id, :phrase, 'migrated', 'accepted', 1, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "asset_group_id": row["asset_group_id"],
                "phrase": row["tag_name"],
                "now": now,
            },
        )


def _upgrade_semantic_profiles() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, image_summary, semantic_profile_json FROM images")
    ).mappings()
    for row in rows:
        try:
            old = json.loads(row["semantic_profile_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            old = {}
        if old.get("schema_version") == 2:
            continue
        profile = {
            "schema_version": 2,
            "visual_facts": old.get("visual_facts")
            or ([row["image_summary"]] if row["image_summary"] else []),
            "ocr_text": [],
            "subjects": [],
            "scenes": [],
            "actions": [],
            "visual_style": [],
            "visible_product_features": [],
            "asset_search_phrases": old.get("search_phrases") or [],
            "negative_visual_concepts": old.get("exclusion_boundaries") or [],
        }
        bind.execute(
            sa.text("UPDATE images SET semantic_profile_json = :profile WHERE id = :id"),
            {
                "id": row["id"],
                "profile": json.dumps(profile, ensure_ascii=False, separators=(",", ":")),
            },
        )


def downgrade() -> None:
    _downgrade_semantic_profiles()
    op.drop_table("asset_search_phrases")
    op.drop_table("asset_concept_links")


def _downgrade_semantic_profiles() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, semantic_profile_json FROM images")).mappings()
    for row in rows:
        try:
            profile = json.loads(row["semantic_profile_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            profile = {}
        if profile.get("schema_version") != 2:
            continue
        legacy_profile = {
            "visual_facts": profile.get("visual_facts") or [],
            "business_intent": "",
            "search_phrases": profile.get("asset_search_phrases") or [],
            "exclusion_boundaries": profile.get("negative_visual_concepts") or [],
        }
        bind.execute(
            sa.text("UPDATE images SET semantic_profile_json = :profile WHERE id = :id"),
            {
                "id": row["id"],
                "profile": json.dumps(legacy_profile, ensure_ascii=False, separators=(",", ":")),
            },
        )
