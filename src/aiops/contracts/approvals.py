"""Approval-related contracts for human-in-the-loop workflows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ApprovalDecisionType = Literal["approve", "reject", "revise"]


class ApprovalDecision(BaseModel):
    """Operator approval decision captured from Bot cards or CLI signals.

    Attributes:
        decision: Operator decision value.
        reason: Optional reason, required for rejects.
        revised_args: Optional replacement arguments, required for revisions.
        approver_user_id: Operator identity emitted by the caller.
    """

    decision: ApprovalDecisionType
    reason: str = ""
    revised_args: dict[str, Any] | None = None
    approver_user_id: str = ""

    @model_validator(mode="after")
    def validate_decision_requirements(self) -> ApprovalDecision:
        """Enforce decision-specific payload requirements."""
        if self.decision == "reject" and not self.reason.strip():
            raise ValueError("reject decisions require a non-empty reason")
        if self.decision == "revise" and self.revised_args is None:
            raise ValueError("revise decisions require revised_args")
        return self


class ApprovalCard(BaseModel):
    """Serializable approval card payload passed to Bot delivery layers.

    Attributes:
        workflow_id: Workflow awaiting a decision.
        title: Card title shown to operators.
        summary: Short summary of the proposed action.
        metadata: Arbitrary metadata used by callback handlers.
    """

    workflow_id: str
    title: str
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
