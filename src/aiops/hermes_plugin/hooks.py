"""Hermes hook callbacks for observability, webhook handling, and lifecycle."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import structlog

from aiops.gateway.hooks import dedupe_and_persist
from aiops.gateway.services import build_service_bundle
from aiops.lifecycle import shutdown
from aiops.observability.langfuse_client import record_gateway_webhook_trace
from aiops.plugins.sanitize import sanitize_prompt_messages


def ping(*_: Any, **__: Any) -> None:
    """No-op hook callback used to validate Hermes hook registration."""


def log_post_tool_call(tool_name: str, params: Mapping[str, Any], result: Any, **_: Any) -> None:
    """Observe tool calls without mutating behavior.

    Args:
        tool_name: Registered Hermes tool name.
        params: Tool parameters passed by Hermes.
        result: Tool return payload.
    """
    del tool_name, params, result


def register_safety_hooks(ctx: Any, *, role: str) -> None:
    """Register hooks that every Hermes instance should get.

    Args:
        ctx: Hermes plugin registration context.
        role: Active Hermes instance role. Currently unused but reserved
            for Task 7 where the LLM-layer kill-switch will scope itself
            by ``kill_switch:hermes_instance:{role}`` and the cost cap
            will tag metrics with the role.
    """
    del role  # reserved for Task 7 LLM-layer kill-switch / cost cap
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("post_tool_call", log_post_tool_call)


async def on_pre_llm_call(session_id: str, user_message: str, conversation_history: Any, **_: Any) -> Any:
    """Sanitize untrusted prompt blocks before Hermes calls the LLM.

    Args:
        session_id: Hermes session identifier.
        user_message: Raw end-user message.
        conversation_history: Prompt container carrying untrusted blocks.

    Returns:
        Sanitized prompt payload, or ``None`` if sanitization fails.
    """
    del session_id
    try:
        return await sanitize_prompt_messages(user_message, conversation_history)
    except Exception as error:  # noqa: BLE001
        structlog.get_logger().error("sanitize_failed", error=str(error))
        return None


async def on_webhook_received(payload: dict[str, Any], route_name: str, **_: Any) -> Any:
    """Hermes lifecycle adapter for gateway webhook ingestion.

    Args:
        payload: Raw webhook payload.
        route_name: Named Hermes route that matched the request.

    Returns:
        The gateway hook result, or ``None`` when the hook fails.
    """
    try:
        service_bundle = await build_service_bundle()
        result = await dedupe_and_persist(payload, route_name, service_bundle)
        try:
            await record_gateway_webhook_trace(
                source_event_id=payload["event"]["eventid"],
                route_name=route_name,
                payload=payload,
                action=result.action,
                risk_level=result.payload.get("_risk_level"),
            )
        except Exception as error:  # noqa: BLE001
            structlog.get_logger().error("langfuse_trace_failed", error=str(error), route_name=route_name)
        return result
    except Exception as error:  # noqa: BLE001
        structlog.get_logger().error("webhook_hook_failed", error=str(error), route_name=route_name)
        return None


async def on_gateway_shutdown(*_: Any, **__: Any) -> None:
    """Hermes lifecycle adapter for orderly process shutdown.

    Drains the shared resource registry (DB engine, Redis pool, NetBox
    httpx client, future Scrapli / Temporal clients). Best-effort: if
    Hermes does not emit ``gateway:shutdown`` for a given build the
    process still functions, but pooled connections may not drain
    gracefully on exit. ``atexit`` / signal-handler-based shutdown is
    intentionally avoided because async cleanup outside a running event
    loop is unsafe.
    """
    try:
        await shutdown()
    except Exception as error:  # noqa: BLE001
        structlog.get_logger().error("aiops_shutdown_failed", error=str(error))


def register_webhook_hooks(ctx: Any) -> None:
    """Register gateway webhook hooks on the Hermes plugin context."""
    ctx.register_hook("gateway:webhook_received", on_webhook_received)
    ctx.register_hook("gateway:shutdown", on_gateway_shutdown)
