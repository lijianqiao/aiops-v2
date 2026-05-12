"""Minimal repository helpers for the Task 3 control-plane schema."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aiops.db.models import Alert, ApprovalRecord, WorkflowRecord


@dataclass(slots=True)
class AlertRepository:
    """Repository for querying and persisting raw alerts."""

    session: AsyncSession

    async def get_by_source_event_id(self, source_event_id: str) -> Alert | None:
        """Return an alert by its idempotency key if it exists."""
        result = await self.session.execute(select(Alert).where(Alert.source_event_id == source_event_id))
        return result.scalar_one_or_none()

    async def add(self, alert: Alert) -> Alert:
        """Persist an alert entity in the current transaction."""
        self.session.add(alert)
        await self.session.flush()
        return alert


@dataclass(slots=True)
class WorkflowRepository:
    """Repository for workflow mirror records."""

    session: AsyncSession

    async def get_by_workflow_id(self, workflow_id: str) -> WorkflowRecord | None:
        """Return a workflow mirror row by Temporal workflow ID."""
        result = await self.session.execute(select(WorkflowRecord).where(WorkflowRecord.workflow_id == workflow_id))
        return result.scalar_one_or_none()


@dataclass(slots=True)
class ApprovalRepository:
    """Repository for approval mirror records written by signal handlers."""

    session: AsyncSession

    async def add(self, approval: ApprovalRecord) -> ApprovalRecord:
        """Persist an approval mirror record in the current transaction."""
        self.session.add(approval)
        await self.session.flush()
        return approval
