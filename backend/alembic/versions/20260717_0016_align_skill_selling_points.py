"""align persisted selling-point phrases with the reviewed skill boundary"""

import sqlalchemy as sa

from alembic import op

revision = "20260717_0016"
down_revision = "20260717_0015"
branch_labels = None
depends_on = None


CONCEPT_CODE = "universal_method"
PHRASES = ("一道题会一类题", "一道题学会一类题")


def upgrade() -> None:
    _set_review_status("accepted", "rejected")


def downgrade() -> None:
    _set_review_status("rejected", "accepted")


def _set_review_status(before: str, after: str) -> None:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "UPDATE concept_search_phrases "
            "SET review_status = :after "
            "WHERE origin = 'source_document' "
            "AND review_status = :before "
            "AND phrase IN (:phrase_one, :phrase_two) "
            "AND concept_id = ("
            "SELECT id FROM business_concepts WHERE code = :concept_code"
            ")"
        ),
        {
            "after": after,
            "before": before,
            "phrase_one": PHRASES[0],
            "phrase_two": PHRASES[1],
            "concept_code": CONCEPT_CODE,
        },
    )
    if result.rowcount is not None and result.rowcount > 0:
        bind.execute(
            sa.text(
                "UPDATE business_concepts "
                "SET version = version + 1, updated_at = CURRENT_TIMESTAMP "
                "WHERE code = :concept_code"
            ),
            {"concept_code": CONCEPT_CODE},
        )
