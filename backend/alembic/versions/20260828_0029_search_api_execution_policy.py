"""expand search API task budgets"""

import sqlalchemy as sa

from alembic import op

revision = "20260828_0029"
down_revision = "20260828_0028"
branch_labels = None
depends_on = None


SEARCH_TASK_BUDGETS = {
    "search_system_routing": (15.0, 45.0),
    "search_intent_understanding": (25.0, 60.0),
    "search_proof_point_understanding": (20.0, 45.0),
    "search_candidate_review": (20.0, 45.0),
    "search_result_recommendation_reason": (20.0, 45.0),
}
ROUTING_SLOTS = sa.table(
    "model_routing_slots",
    sa.column("task", sa.String()),
    sa.column("timeout_seconds", sa.Float()),
)


def upgrade() -> None:
    for task, (old_budget, new_budget) in SEARCH_TASK_BUDGETS.items():
        op.execute(
            ROUTING_SLOTS.update()
            .where(ROUTING_SLOTS.c.task == task)
            .where(ROUTING_SLOTS.c.timeout_seconds <= old_budget)
            .values(timeout_seconds=new_budget)
        )


def downgrade() -> None:
    for task, (old_budget, new_budget) in SEARCH_TASK_BUDGETS.items():
        op.execute(
            ROUTING_SLOTS.update()
            .where(ROUTING_SLOTS.c.task == task)
            .where(ROUTING_SLOTS.c.timeout_seconds == new_budget)
            .values(timeout_seconds=old_budget)
        )
