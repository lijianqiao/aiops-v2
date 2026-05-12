"""Langfuse client lifecycle and webhook trace helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from langfuse import Langfuse

from aiops.lifecycle import ResourceRegistry, get_global_registry
from aiops.settings import Settings

_langfuse_client: Langfuse | None = None


def build_langfuse_client(
    settings: Settings | None = None,
    *,
    registry: ResourceRegistry | None = None,
) -> Langfuse | None:
    """Build and cache the process-wide Langfuse client.

    Returns ``None`` when Langfuse credentials are unset so local bootstraps
    without observability still function.
    """
    global _langfuse_client
    if _langfuse_client is None:
        active_settings = settings or Settings()
        public_key = active_settings.langfuse_public_key.strip()
        secret_key = active_settings.langfuse_secret_key.get_secret_value().strip()
        if not public_key or not secret_key:
            return None

        active_registry = registry if registry is not None else get_global_registry()
        _langfuse_client = Langfuse(
            host=active_settings.langfuse_host,
            public_key=public_key,
            secret_key=secret_key,
        )
        active_registry.register("langfuse_client", dispose_langfuse_client)
    return _langfuse_client


async def dispose_langfuse_client() -> None:
    """Flush and shut down the cached Langfuse client."""
    global _langfuse_client
    if _langfuse_client is not None:
        client = _langfuse_client
        _langfuse_client = None
        await asyncio.to_thread(client.shutdown)


async def record_gateway_webhook_trace(
    *,
    source_event_id: str,
    route_name: str,
    payload: dict[str, Any],
    action: str,
    risk_level: str | None,
) -> str | None:
    """Emit a deterministic Langfuse trace for one gateway webhook event."""
    client = build_langfuse_client()
    if client is None:
        return None

    trace_id = Langfuse.create_trace_id(seed=source_event_id)
    output_payload = {"action": action, "route_name": route_name, "risk_level": risk_level}
    await asyncio.to_thread(
        client.create_event,
        name="gateway:webhook_received",
        input=payload,
        output=output_payload,
        metadata={"source_event_id": source_event_id, "route_name": route_name},
        trace_context={"trace_id": trace_id},
    )
    await asyncio.to_thread(client.flush)
    return trace_id
