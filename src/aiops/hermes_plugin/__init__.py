"""Hermes plugin entry point for AIOps integration boundary probing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiops.hermes_plugin import hooks, tools


def _register_hooks(ctx: Any) -> list[str]:
    """Register minimal Hermes hooks for Task 0.

    Args:
        ctx: Hermes plugin context.

    Returns:
        Hook names exposed by the plugin.
    """
    ctx.register_hook("gateway:webhook_received", hooks.ping)
    ctx.register_hook("post_tool_call", hooks.log_post_tool_call)

    return ["gateway:webhook_received", "post_tool_call"]


def _register_tools(ctx: Any) -> list[str]:
    """Register a minimal ping tool for Task 0.

    Args:
        ctx: Hermes plugin context.

    Returns:
        Tool names exposed by the plugin.
    """
    ctx.register_tool(
        name="aiops_ping",
        toolset="aiops",
        schema=tools.PING_TOOL_SCHEMA,
        handler=tools.aiops_ping,
        description="Return a static pong payload for AIOps Hermes integration checks.",
    )

    return ["aiops_ping"]


def _register_cli(ctx: Any) -> list[str]:
    """Register the Task 0 plugin CLI surface.

    Hermes currently exposes plugin CLI registration via ``ctx.register_cli_command``.
    Task 0 does not add a live command tree yet; this only proves the plugin can
    register optional CLI integration without failing discovery.

    Args:
        ctx: Hermes plugin context.

    Returns:
        Registered CLI root names.
    """
    if hasattr(ctx, "register_cli_command"):
        ctx.register_cli_command(
            name="aiops",
            help="AIOps plugin management commands.",
            setup_fn=lambda parser: parser,
            handler_fn=lambda args: args,
        )

    return ["aiops"]


def bundled_skill_paths() -> list[str]:
    """Return the plugin-bundled skill files shipped with the package."""
    skill_path = Path(__file__).resolve().parent.parent / "bot" / "skills" / "aiops-ping" / "SKILL.md"
    return [str(skill_path)]


def register(ctx: Any) -> None:
    """Register the full AIOps Hermes plugin.

    Hermes expects one plugin entry point whose target exposes ``register(ctx)``.

    Args:
        ctx: Hermes plugin registration context.
    """
    _register_hooks(ctx)
    _register_tools(ctx)
    _register_cli(ctx)
