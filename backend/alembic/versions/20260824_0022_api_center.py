"""add api center provider management"""

import sqlalchemy as sa

from alembic import op

revision = "20260824_0022"
down_revision = "20260805_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_api_credentials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=40), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("api_key_secret", sa.Text(), nullable=False),
        sa.Column("api_key_preview", sa.String(length=32), nullable=False),
        sa.Column("task_scope_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("auto_assign_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_status", sa.String(length=24), nullable=True),
        sa.Column("last_latency_ms", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(length=300), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_api_credentials_label", "model_api_credentials", ["label"])
    op.create_index("ix_model_api_credentials_model_name", "model_api_credentials", ["model_name"])
    op.create_index("ix_model_api_credentials_priority", "model_api_credentials", ["priority"])
    op.create_index(
        "ix_model_api_credentials_provider_type",
        "model_api_credentials",
        ["provider_type"],
    )
    op.create_index("ix_model_api_credentials_status", "model_api_credentials", ["status"])
    op.create_index(
        "ix_model_api_credentials_auto_assign_enabled",
        "model_api_credentials",
        ["auto_assign_enabled"],
    )
    op.create_index(
        "ix_model_api_credentials_last_status",
        "model_api_credentials",
        ["last_status"],
    )

    op.create_table(
        "model_routing_slots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("primary_credential_id", sa.String(length=36), nullable=True),
        sa.Column("backup_credential_ids_json", sa.Text(), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=False),
        sa.Column("hedging_delay_ms", sa.Integer(), nullable=False),
        sa.Column("max_parallel", sa.Integer(), nullable=False),
        sa.Column("auto_select_enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["primary_credential_id"],
            ["model_api_credentials.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task"),
    )
    op.create_index("ix_model_routing_slots_task", "model_routing_slots", ["task"], unique=True)
    op.create_index(
        "ix_model_routing_slots_primary_credential_id",
        "model_routing_slots",
        ["primary_credential_id"],
    )
    op.create_index(
        "ix_model_routing_slots_auto_select_enabled",
        "model_routing_slots",
        ["auto_select_enabled"],
    )

    op.create_table(
        "model_api_health_checks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("credential_id", sa.String(length=36), nullable=False),
        sa.Column("task", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.String(length=300), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["model_api_credentials.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_api_health_checks_checked_at",
        "model_api_health_checks",
        ["checked_at"],
    )
    op.create_index(
        "ix_model_api_health_checks_credential_id",
        "model_api_health_checks",
        ["credential_id"],
    )
    op.create_index(
        "ix_model_api_health_checks_duration_ms",
        "model_api_health_checks",
        ["duration_ms"],
    )
    op.create_index("ix_model_api_health_checks_status", "model_api_health_checks", ["status"])
    op.create_index("ix_model_api_health_checks_task", "model_api_health_checks", ["task"])

    op.create_table(
        "model_call_traces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("search_log_id", sa.String(length=36), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("task", sa.String(length=80), nullable=False),
        sa.Column("layer_name", sa.String(length=120), nullable=False),
        sa.Column("credential_id", sa.String(length=36), nullable=True),
        sa.Column("credential_label", sa.String(length=120), nullable=True),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("fallback_index", sa.Integer(), nullable=True),
        sa.Column("error_summary", sa.String(length=300), nullable=True),
        sa.Column("response_valid", sa.Boolean(), nullable=True),
        sa.Column("output_summary_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["model_api_credentials.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["search_log_id"],
            ["search_logs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_call_traces_created_at", "model_call_traces", ["created_at"])
    op.create_index("ix_model_call_traces_credential_id", "model_call_traces", ["credential_id"])
    op.create_index("ix_model_call_traces_duration_ms", "model_call_traces", ["duration_ms"])
    op.create_index("ix_model_call_traces_model", "model_call_traces", ["model"])
    op.create_index("ix_model_call_traces_provider", "model_call_traces", ["provider"])
    op.create_index("ix_model_call_traces_request_id", "model_call_traces", ["request_id"])
    op.create_index("ix_model_call_traces_search_log_id", "model_call_traces", ["search_log_id"])
    op.create_index("ix_model_call_traces_status", "model_call_traces", ["status"])
    op.create_index("ix_model_call_traces_task", "model_call_traces", ["task"])


def downgrade() -> None:
    op.drop_index("ix_model_call_traces_task", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_status", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_search_log_id", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_request_id", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_provider", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_model", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_duration_ms", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_credential_id", table_name="model_call_traces")
    op.drop_index("ix_model_call_traces_created_at", table_name="model_call_traces")
    op.drop_table("model_call_traces")

    op.drop_index("ix_model_api_health_checks_task", table_name="model_api_health_checks")
    op.drop_index("ix_model_api_health_checks_status", table_name="model_api_health_checks")
    op.drop_index("ix_model_api_health_checks_duration_ms", table_name="model_api_health_checks")
    op.drop_index("ix_model_api_health_checks_credential_id", table_name="model_api_health_checks")
    op.drop_index("ix_model_api_health_checks_checked_at", table_name="model_api_health_checks")
    op.drop_table("model_api_health_checks")

    op.drop_index("ix_model_routing_slots_auto_select_enabled", table_name="model_routing_slots")
    op.drop_index("ix_model_routing_slots_primary_credential_id", table_name="model_routing_slots")
    op.drop_index("ix_model_routing_slots_task", table_name="model_routing_slots")
    op.drop_table("model_routing_slots")

    op.drop_index("ix_model_api_credentials_last_status", table_name="model_api_credentials")
    op.drop_index(
        "ix_model_api_credentials_auto_assign_enabled",
        table_name="model_api_credentials",
    )
    op.drop_index("ix_model_api_credentials_status", table_name="model_api_credentials")
    op.drop_index("ix_model_api_credentials_provider_type", table_name="model_api_credentials")
    op.drop_index("ix_model_api_credentials_priority", table_name="model_api_credentials")
    op.drop_index("ix_model_api_credentials_model_name", table_name="model_api_credentials")
    op.drop_index("ix_model_api_credentials_label", table_name="model_api_credentials")
    op.drop_table("model_api_credentials")
