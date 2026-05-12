"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-12 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the initial control-plane schema."""
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("source_event_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'open'"), nullable=False),
        sa.Column("risk_level", sa.String(length=8), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("incident_id", name="pk_incidents"),
    )
    op.create_table(
        "workflows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("source_event_id", sa.String(length=255), nullable=True),
        sa.Column("workflow_name", sa.String(length=255), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=8), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.incident_id"], name="fk_workflows_incident_id_incidents"),
        sa.PrimaryKeyConstraint("id", name="pk_workflows"),
        sa.UniqueConstraint("workflow_id", name="uq_workflows_workflow_id"),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("source_event_id", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("route_name", sa.String(length=128), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("trigger_name", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.incident_id"], name="fk_alerts_incident_id_incidents"),
        sa.PrimaryKeyConstraint("id", name="pk_alerts"),
        comment="Raw alerts. Planned monthly partitioning in PostgreSQL.",
    )
    op.create_index("ix_alerts_source_event_id", "alerts", ["source_event_id"], unique=True)
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=False),
        sa.Column("signal_id", sa.String(length=255), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("approver_user_id", sa.String(length=255), nullable=True),
        sa.Column("revised_args", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.workflow_id"], name="fk_approvals_workflow_id_workflows"),
        sa.PrimaryKeyConstraint("id", name="pk_approvals"),
        sa.UniqueConstraint("workflow_id", "signal_id", name="uq_approvals_workflow_id_signal_id"),
    )
    op.create_table(
        "skills_staging",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_incident_id", sa.String(length=64), nullable=True),
        sa.Column("review_status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_incident_id"], ["incidents.incident_id"], name="fk_skills_staging_source_incident_id_incidents"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_skills_staging"),
        sa.UniqueConstraint("slug", name="uq_skills_staging_slug"),
    )
    op.create_table(
        "skills_active",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("promoted_from_staging_id", sa.Integer(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["promoted_from_staging_id"],
            ["skills_staging.id"],
            name="fk_skills_active_promoted_from_staging_id_skills_staging",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_skills_active"),
        sa.UniqueConstraint("slug", name="uq_skills_active_slug"),
    )
    op.create_table(
        "rca_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.incident_id"], name="fk_rca_reports_incident_id_incidents"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rca_reports"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_event_id", sa.String(length=255), nullable=True),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("workflow_id", sa.String(length=255), nullable=True),
        sa.Column("activity_name", sa.String(length=255), nullable=True),
        sa.Column("trace_id", sa.String(length=255), nullable=True),
        sa.Column("log_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=True),
        sa.Column("simulated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.incident_id"], name="fk_audit_logs_incident_id_incidents"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        comment="Monthly partitioned audit log table managed by pg_partman.",
    )
    op.create_index("ix_audit_logs_source_event_id", "audit_logs", ["source_event_id"], unique=False)
    op.create_index("ix_audit_logs_workflow_id", "audit_logs", ["workflow_id"], unique=False)
    op.create_table(
        "device_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_name", sa.String(length=255), nullable=False),
        sa.Column("workflow_id", sa.String(length=255), nullable=True),
        sa.Column("action_id", sa.String(length=64), nullable=True),
        sa.Column("config_blob", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_device_configs"),
    )
    op.create_index("ix_device_configs_device_name", "device_configs", ["device_name"], unique=False)
    op.create_table(
        "cost_ledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("source_event_id", sa.String(length=255), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.incident_id"], name="fk_cost_ledger_incident_id_incidents"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cost_ledger"),
    )
    op.create_table(
        "eval_dataset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("source_event_id", sa.String(length=255), nullable=True),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("expected_output", sa.JSON(), nullable=True),
        sa.Column("actual_output", sa.JSON(), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.incident_id"], name="fk_eval_dataset_incident_id_incidents"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_eval_dataset"),
    )
    op.create_table(
        "fastpath_hits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("source_event_id", sa.String(length=255), nullable=True),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("matched", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.incident_id"], name="fk_fastpath_hits_incident_id_incidents"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fastpath_hits"),
    )
    op.create_index("ix_fastpath_hits_rule_id", "fastpath_hits", ["rule_id"], unique=False)
    op.create_table(
        "agent_memory_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hermes_instance", sa.String(length=255), nullable=False),
        sa.Column("trace_id", sa.String(length=255), nullable=True),
        sa.Column("archive_blob", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_agent_memory_snapshots"),
    )
    op.create_index(
        "ix_agent_memory_snapshots_hermes_instance", "agent_memory_snapshots", ["hermes_instance"], unique=False
    )


def downgrade() -> None:
    """Drop the initial control-plane schema."""
    op.drop_index("ix_agent_memory_snapshots_hermes_instance", table_name="agent_memory_snapshots")
    op.drop_table("agent_memory_snapshots")
    op.drop_index("ix_fastpath_hits_rule_id", table_name="fastpath_hits")
    op.drop_table("fastpath_hits")
    op.drop_table("eval_dataset")
    op.drop_table("cost_ledger")
    op.drop_index("ix_device_configs_device_name", table_name="device_configs")
    op.drop_table("device_configs")
    op.drop_index("ix_audit_logs_workflow_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_source_event_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("rca_reports")
    op.drop_table("skills_active")
    op.drop_table("skills_staging")
    op.drop_table("approvals")
    op.drop_index("ix_alerts_source_event_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("workflows")
    op.drop_table("incidents")
