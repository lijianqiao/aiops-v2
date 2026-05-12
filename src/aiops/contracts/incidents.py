"""Incident and execution contracts for workflow orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

RiskLevel = Literal["L1", "L2", "L3"]
IncidentSource = Literal["zabbix", "manual", "cron", "internal"]


class IncidentEnvelope(BaseModel):
    """Normalized incident envelope persisted and replayed across workflows.

    Attributes:
        incident_id: Internal human-facing incident identifier.
        source_event_id: Source-side idempotency key.
        source: Origin of the incident trigger.
        received_at: Time the platform received the event.
        raw_payload: Original payload retained for audit and replay.
    """

    incident_id: str
    source_event_id: str
    source: IncidentSource
    received_at: datetime
    raw_payload: dict[str, Any]


class ExecutionContext(BaseModel):
    """Typed execution semantics passed from workflows into activities.

    Attributes:
        risk_level: Resolved risk level for the execution path.
        requires_approval: Whether the plan must wait for human approval.
    """

    risk_level: RiskLevel
    requires_approval: bool


class RepairAction(BaseModel):
    """Single executable repair step inside a workflow plan.

    Attributes:
        action_id: Unique action identifier used for audit, caching, and rollback.
        tool: Registered tool name that should execute the step.
        args: JSON-serializable input arguments for the tool.
        target_device: Target host or network device identifier.
        rollback_args: Optional rollback payload for reversible operations.
    """

    action_id: UUID
    tool: str
    args: dict[str, Any]
    target_device: str
    rollback_args: dict[str, Any] | None


class RepairPlan(BaseModel):
    """Top-level repair plan produced by fast-path rules or agent reasoning.

    Attributes:
        envelope: Shared incident envelope carrying idempotency metadata.
        risk_level: Resolved plan risk level.
        requires_approval: Whether execution must wait for human approval.
        dry_run: Simulated execution toggle recognized by workflows and policies.
        root_cause: Human-readable diagnosis summary.
        actions: Ordered repair steps to execute. A plan must carry at least
            one action; read-only assessments belong in a separate diagnosis
            artifact, not in ``RepairPlan`` (architecture §4.4).
        confidence: Confidence score in the produced diagnosis and plan.
        reference_skills: Non-empty list of SOP or wiki references backing the plan.
    """

    envelope: IncidentEnvelope
    risk_level: RiskLevel
    requires_approval: bool
    dry_run: bool = False
    root_cause: str
    actions: list[RepairAction] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    reference_skills: list[str] = Field(min_length=1)
