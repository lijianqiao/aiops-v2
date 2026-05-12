"""SQLAlchemy 2.0 models for the AIOps control-plane database."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by all control-plane models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Common timestamp columns for persisted records."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Alert(Base):
    """Raw upstream alert persisted for idempotency and audit.

    ``severity`` mirrors the upstream alert severity reported by Zabbix
    (warning / high / disaster). ``risk_level`` is the platform-derived
    execution risk floor (L1 / L2 / L3) used by Fast Path and the
    Execution Policy Interceptor — the two fields must stay distinct so
    SQL queries and Prometheus labels can distinguish source data from
    derived decisions.
    """

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_source_event_id", "source_event_id", unique=True),
        {"comment": "Raw alerts. Planned monthly partitioning in PostgreSQL."},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True)
    source_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    route_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trigger_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Incident(Base, TimestampMixin):
    """Aggregated incident record referencing one or more raw alerts."""

    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'open'"))
    risk_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkflowRecord(Base, TimestampMixin):
    """Mirror record for Temporal workflow execution metadata."""

    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ApprovalRecord(Base):
    """Mirror of workflow approval signals written by the signal handler."""

    __tablename__ = "approvals"
    __table_args__ = (UniqueConstraint("workflow_id", "signal_id", name="uq_approvals_workflow_id_signal_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.workflow_id"), nullable=False)
    signal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approver_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revised_args: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SkillStaging(Base, TimestampMixin):
    """Pending auto-generated skills awaiting operator review."""

    __tablename__ = "skills_staging"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'pending'"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SkillActive(Base, TimestampMixin):
    """Promoted skills available to the live system."""

    __tablename__ = "skills_active"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    promoted_from_staging_id: Mapped[int | None] = mapped_column(ForeignKey("skills_staging.id"), nullable=True)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RCAReport(Base, TimestampMixin):
    """Persisted RCA markdown generated for an incident."""

    __tablename__ = "rca_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.incident_id"), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class AuditLog(Base):
    """Full audit log covering prompt, tool, and execution events."""

    __tablename__ = "audit_logs"
    __table_args__ = ({"comment": "Monthly partitioned audit log table managed by pg_partman."},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True)
    workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    activity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    log_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeviceConfig(Base):
    """Configuration snapshot captured before network changes."""

    __tablename__ = "device_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    config_blob: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CostLedger(Base):
    """Per-incident LLM usage and cost accounting."""

    __tablename__ = "cost_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EvalDatasetRecord(Base, TimestampMixin):
    """Persisted evaluation sample and verdict."""

    __tablename__ = "eval_dataset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    expected_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    actual_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)


class FastPathHit(Base):
    """Fast-path classification match statistics."""

    __tablename__ = "fastpath_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"), nullable=True)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentMemorySnapshot(Base):
    """Compressed memory directory snapshot for a Hermes instance."""

    __tablename__ = "agent_memory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hermes_instance: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archive_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
