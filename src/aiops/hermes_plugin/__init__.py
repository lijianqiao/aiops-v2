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

from aiops.hermes_plugin import commands_registry, hooks, tools, tools_registry
from aiops.settings import HermesRole, Settings


def _read_role() -> HermesRole:
    """Return the instance role from typed application settings.

    Pydantic validates the ``Literal`` membership at Settings construction
    time, so an unknown role fails loud here rather than silently loading
    the wrong subset.
    """
    return Settings().hermes_instance


def _register_always_on(ctx: Any, role: HermesRole) -> None:
    """Register hooks and tools that every Hermes instance gets.

    Currently wired:
        - ``aiops_ping`` tool (Task 0 connectivity probe)
        - ``pre_llm_call`` prompt-injection sanitizer (Task 5)
        - ``post_tool_call`` observability hook (Task 0)

    Task 7 / 8 / 9 will add the LLM-layer kill-switch, cost cap, and
    ``pre_tool_call`` hallucination guard alongside the existing hooks.
    """
    hooks.register_safety_hooks(ctx, role=role)

    ctx.register_tool(
        name="aiops_ping",
        toolset="aiops",
        schema=tools.PING_TOOL_SCHEMA,
        handler=tools.aiops_ping,
        description="Return a static pong payload for AIOps Hermes integration checks.",
    )


def _register_gateway(ctx: Any) -> None:
    """Register hooks and commands specific to the gateway role.

    The gateway instance owns webhook ingestion (Task 4
    ``gateway:webhook_received``) and the 飞书 Bot slash command surface
    (Task 5 ``ctx.register_command``). Business tool credentials must
    NOT be loaded here (§6.3).
    """
    hooks.register_webhook_hooks(ctx)
    commands_registry.register_bot_commands(ctx)


def _register_linux(ctx: Any) -> None:
    """Register Linux / Windows server tools.

    Task 5 wires the read-only triage tools (``get_disk_usage``,
    ``get_systemd_status``). Task 9 will add the write tools
    (``restart_service``, ``cleanup_disk``) once the production
    :class:`LinuxTransport` wrapper lands.
    """
    tools_registry.register_linux_tools(ctx)


def _register_network(ctx: Any) -> None:
    """Register network device tools (H3C / Huawei / Cisco).

    Task 5 wires the read-only triage tools (``get_interface_status``,
    ``get_ospf_neighbors``). Task 9 will add the write tools
    (``shutdown_interface``, etc.) using the Scrapli-backed
    :class:`NetworkTransport` wrapper.
    """
    tools_registry.register_network_tools(ctx)


def _register_infra(ctx: Any) -> None:
    """Register DB / Zabbix-self tools.

    Task 5 leaves this as a placeholder; concrete handlers
    (``pg_check_replication_lag``, ``redis_inspect_memory``) land in a
    later iteration once the infra service bundle stabilizes.
    """
    tools_registry.register_infra_tools(ctx)


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

    _register_always_on(ctx, role)
    _ROLE_DISPATCH[role](ctx)
    _register_cli(ctx)
