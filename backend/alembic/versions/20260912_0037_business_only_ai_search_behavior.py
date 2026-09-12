"""limit AI Search behavior outbox to business users

Revision ID: 20260912_0037
Revises: 20260911_0036
Create Date: 2026-09-12 11:05:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260912_0037"
down_revision = "20260911_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The durable outbox is a transport buffer, not the source analytics log.
    # Remove legacy non-business rows before they can reach the external dataset;
    # the corresponding user_usage_events remain available to local operations.
    op.execute(
        sa.text(
            """
            DELETE FROM ai_search_behavior_events
            WHERE NOT EXISTS (
                SELECT 1
                FROM users
                WHERE users.id = ai_search_behavior_events.user_id
                  AND users.role = 'business'
            )
            """
        )
    )


def downgrade() -> None:
    # Purged transport rows are intentionally not reconstructed. Source analytics
    # remain in user_usage_events and the eligibility rule lives in the service.
    pass
