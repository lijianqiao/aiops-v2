"""Hermes plugin entry point for AIOps integration.

Per architecture §5.5: a single ``register(ctx)`` callable is exposed via the
``hermes_agent.plugins`` entry-point group. ``register`` is called exactly
once at Hermes startup and dispatches registration by the instance role
declared in ``AIOPS_HERMES_INSTANCE`` (gateway / linux / network / infra).
The role is read through the typed :class:`aiops.settings.Settings` model so
that Pydantic validates the value once at the system edge — this is the
single source of truth (architecture §5.5.4 / §6.3).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from aiops.hermes_plugin import hooks, tools
from aiops.settings import HermesRole, Settings


def _read_role() -> HermesRole:
    """Return the instance role from typed application settings.

    Pydantic validates the ``Literal`` membership at Settings construction
    time, so an unknown role fails loud here rather than silently loading
    the wrong subset.
    """
    return Settings().hermes_instance


def _register_always_on(ctx: Any) -> None:
    """Register hooks and tools that every Hermes instance gets.

    Task 0 surface: the ``aiops_ping`` tool and a no-op ``post_tool_call``
    hook act as a connectivity probe. Subsequent tasks (4 / 5 / 7) add
    safety hooks here: ``pre_llm_call`` (prompt injection), kill-switch LLM
    layer, cost cap, and ``pre_tool_call`` (hallucination guard early-fail).
    """
    ctx.register_hook("post_tool_call", hooks.log_post_tool_call)

    ctx.register_tool(
        name="aiops_ping",
        toolset="aiops",
        schema=tools.PING_TOOL_SCHEMA,
        handler=tools.aiops_ping,
        description="Return a static pong payload for AIOps Hermes integration checks.",
    )


def _register_gateway(ctx: Any) -> None:
    """Register hooks and commands specific to the gateway role.

    The gateway instance owns webhook ingestion and the 飞书 Bot command
    surface. Business tool credentials must NOT be loaded here (§6.3).
    Task 4 fills in the real ``gateway:webhook_received`` body; Task 5
    fills in slash commands via ``ctx.register_command``.
    """
    ctx.register_hook("gateway:webhook_received", hooks.ping)


def _register_linux(ctx: Any) -> None:
    """Register Linux / Windows server tools. Filled in by Task 5 (read-only) and Task 9 (writes)."""
    # Task 5: ctx.register_tool(name="get_disk_usage", schema=..., handler=...)
    # Task 5: ctx.register_tool(name="get_systemd_status", schema=..., handler=...)
    # Task 9: ctx.register_tool(name="restart_service", schema=..., handler=...)
    # Task 9: ctx.register_tool(name="cleanup_disk", schema=..., handler=...)
    return None


def _register_network(ctx: Any) -> None:
    """Register network device tools (H3C / Huawei / Cisco). Filled in by Task 5 / 9."""
    # Task 5: ctx.register_tool(name="get_interface_status", ...)
    # Task 5: ctx.register_tool(name="get_ospf_neighbors", ...)
    # Task 9: ctx.register_tool(name="shutdown_interface", ...)
    return None


def _register_infra(ctx: Any) -> None:
    """Register DB / Zabbix-self tools. Filled in by Task 5."""
    # Task 5: ctx.register_tool(name="pg_check_replication_lag", ...)
    # Task 5: ctx.register_tool(name="redis_inspect_memory", ...)
    return None


def _register_cli(ctx: Any) -> None:
    """Register the ``hermes aiops`` CLI surface.

    Hermes exposes plugin CLI registration via ``ctx.register_cli_command``.
    Task 0 only proves the binding works; real subcommands land in Task 10.
    """
    if hasattr(ctx, "register_cli_command"):
        ctx.register_cli_command(
            name="aiops",
            help="AIOps plugin management commands.",
            setup_fn=lambda parser: parser,
            handler_fn=lambda args: args,
        )


def bundled_skill_paths() -> list[str]:
    """Return the plugin-bundled skill files shipped with the package."""
    skill_path = Path(__file__).resolve().parent.parent / "bot" / "skills" / "aiops-ping" / "SKILL.md"
    return [str(skill_path)]


_ROLE_DISPATCH: dict[HermesRole, Callable[[Any], None]] = {
    "gateway": _register_gateway,
    "linux": _register_linux,
    "network": _register_network,
    "infra": _register_infra,
}


def register(ctx: Any) -> None:
    """Register the AIOps Hermes plugin with role-aware loading.

    Hermes calls this exactly once at startup. Per §5.5.4 we dispatch by the
    ``AIOPS_HERMES_INSTANCE`` environment variable so a single plugin
    package can be deployed to four systemd units while keeping their tool
    subsets (and therefore credential reach) physically isolated.

    Args:
        ctx: Hermes plugin registration context.
    """
    role = _read_role()

    _register_always_on(ctx)
    _ROLE_DISPATCH[role](ctx)
    _register_cli(ctx)
