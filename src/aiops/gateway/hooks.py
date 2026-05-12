"""Webhook gateway hooks for idempotency, dedupe, and risk enrichment."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from aiops.cmdb.netbox_client import NetBoxDevice
from aiops.gateway.services import GatewayServices, build_services

__all__ = [
    "GatewayHookResult",
    "GatewayServices",
    "build_services",
    "classify_risk",
    "dedupe_and_persist",
]

GatewayAction = Literal["CONTINUE", "RETURN_CACHED", "SKIP"]


@dataclass(slots=True)
class GatewayHookResult:
    """Outcome returned by the webhook dedupe hook.

    Attributes:
        action: Routing decision after idempotency and dedupe checks.
        payload: Payload to continue processing, enriched when applicable.
    """

    action: GatewayAction
    payload: dict[str, Any]


def _extract_source_event_id(payload: dict[str, Any]) -> str:
    """Extract the upstream event identifier from a webhook payload."""
    event = payload.get("event", {})
    event_id = event.get("eventid")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("payload.event.eventid is required")
    return event_id


def _extract_host_name(payload: dict[str, Any]) -> str:
    """Extract the host name from a webhook payload."""
    host = payload.get("host", {})
    host_name = host.get("host")
    if not isinstance(host_name, str) or not host_name:
        raise ValueError("payload.host.host is required")
    return host_name


def _payload_severity(payload: dict[str, Any]) -> str:
    """Return the lowercase upstream severity, or an empty string when absent."""
    raw = payload.get("trigger", {}).get("severity", "")
    return raw.lower() if isinstance(raw, str) else ""


def classify_risk(payload: dict[str, Any], device: NetBoxDevice | None) -> str:
    """Derive the execution risk floor from NetBox metadata and payload signals.

    The result is the *maximum* of two independent escalators:

    - NetBox device role (architecture §12.5): ``core`` → L3,
      ``aggregation`` → L2, anything else → L1.
    - Upstream alert severity: ``disaster`` → L3, ``high`` → L2,
      everything else neutral.

    Either signal can escalate; neither can downgrade an already-escalated
    plan. ``device=None`` (host not in NetBox) collapses the role signal
    to L1 but leaves severity intact so a ``disaster`` alert on an
    unknown host still routes to L3.

    Args:
        payload: Incoming webhook payload.
        device: NetBox device projection, or ``None`` when unknown.

    Returns:
        One of ``L1``, ``L2``, or ``L3``.
    """
    role = device.role if device is not None else None
    severity = _payload_severity(payload)

    if role == "core" or severity == "disaster":
        return "L3"
    if role == "aggregation" or severity == "high":
        return "L2"
    return "L1"


async def dedupe_and_persist(
    payload: dict[str, Any],
    route_name: str,
    service_bundle: GatewayServices,
) -> GatewayHookResult:
    """Apply idempotency, Redis dedupe, NetBox enrichment, and alert persistence.

    Logic order follows architecture §9.3:

    1. DB idempotency check by ``source_event_id``.
    2. Redis five-minute dedupe window.
    3. NetBox device lookup.
    4. Risk derivation from device role and alert severity.
    5. Persist the enriched alert payload with ``risk_level`` and
       ``severity`` carried on dedicated DB columns.

    Args:
        payload: Raw webhook payload.
        route_name: Named Hermes route that accepted the webhook.
        service_bundle: Runtime dependencies used by the hook.

    Returns:
        Routing decision and payload to continue processing.
    """
    source_event_id = _extract_source_event_id(payload)
    host_name = _extract_host_name(payload)

    if await service_bundle.db.alert_exists(source_event_id):
        cached_payload = await service_bundle.db.get_cached_result(source_event_id)
        return GatewayHookResult(action="RETURN_CACHED", payload=cached_payload)

    dedupe_key = f"aiops:webhook_dedupe:{route_name}:{source_event_id}"
    inserted = await service_bundle.redis.set(dedupe_key, "1", ex=300, nx=True)
    if not inserted:
        return GatewayHookResult(action="SKIP", payload=payload)

    device = await service_bundle.netbox.get_device(host_name)
    risk_level = classify_risk(payload, device)
    severity = payload.get("trigger", {}).get("severity")

    enriched_payload = deepcopy(payload)
    enriched_payload["_risk_level"] = risk_level
    enriched_payload["_route_name"] = route_name
    if device is not None:
        enriched_payload["_device_role"] = device.role
        enriched_payload["_device_manufacturer"] = device.manufacturer

    await service_bundle.db.insert_alert(
        source_event_id=source_event_id,
        route_name=route_name,
        host=host_name,
        trigger_name=payload.get("trigger", {}).get("name"),
        risk_level=risk_level,
        severity=severity,
        raw_payload=enriched_payload,
    )
    return GatewayHookResult(action="CONTINUE", payload=enriched_payload)
