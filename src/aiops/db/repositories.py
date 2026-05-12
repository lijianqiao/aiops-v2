"""Repository helpers for the control-plane schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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

    async def alert_exists(self, source_event_id: str) -> bool:
        """Return whether an alert with the idempotency key already exists."""
        return await self.get_by_source_event_id(source_event_id) is not None

    async def get_cached_result(self, source_event_id: str) -> dict[str, Any]:
        """Return the previously persisted raw payload for the alert.

        Raises:
            LookupError: If the source event does not exist.
        """
        alert = await self.get_by_source_event_id(source_event_id)
        if alert is None:
            raise LookupError(f"Alert not found for source_event_id={source_event_id}")
        return alert.raw_payload

    async def add(self, alert: Alert) -> Alert:
        """Persist an alert entity in the current transaction."""
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def insert_alert(
        self,
        *,
        source_event_id: str,
        source: str,
        route_name: str,
        host: str | None,
        trigger_name: str | None,
        raw_payload: dict[str, Any],
        severity: str | None = None,
        risk_level: str | None = None,
    ) -> Alert:
        """Create and persist a new alert row for webhook ingestion.

        Args:
            source_event_id: Upstream idempotency key (e.g. Zabbix event id).
            source: Logical source identifier derived from the route name.
            route_name: Hermes webhook route that accepted the alert.
            host: Inbound host name from the payload.
            trigger_name: Upstream trigger name when available.
            raw_payload: Enriched payload to retain for audit / replay.
            severity: Upstream-reported severity (warning / high / disaster).
            risk_level: Platform-derived execution risk floor (L1 / L2 / L3).
        """
        alert = Alert(
            source_event_id=source_event_id,
            source=source,
            route_name=route_name,
            host=host,
            trigger_name=trigger_name,
            severity=severity,
            risk_level=risk_level,
            raw_payload=raw_payload,
        )
        return await self.add(alert)


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
