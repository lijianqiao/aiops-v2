"""Hermes plugin entry points for AIOps integration boundary probing.

The external Hermes VM will load these functions through the
``hermes_agent.plugins`` entry-point group. Task 0 keeps the implementation
minimal and side-effect free so discovery can be validated before deeper
integration work begins.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aiops.hermes_plugin import hooks, tools


def register_hooks(ctx: Any | None = None) -> list[str]:
    """Register minimal Hermes hooks when a plugin context is provided.

    Args:
        ctx: Hermes plugin context. When absent, the function returns the
            boundary names that would be registered.

    Returns:
        Hook names exposed by the plugin.
    """
    if ctx is not None:
        ctx.register_hook("gateway:webhook_received", hooks.ping)
        ctx.register_hook("post_tool_call", hooks.log_post_tool_call)

    return ["gateway:webhook_received", "post_tool_call"]


def register_tools(ctx: Any | None = None) -> list[str]:
    """Register a minimal ping tool when a plugin context is provided.

    Args:
        ctx: Hermes plugin context.

    Returns:
        Tool names exposed by the plugin.
    """
    if ctx is not None:
        ctx.register_tool(
            name="aiops_ping",
            toolset="aiops",
            schema=tools.PING_TOOL_SCHEMA,
            handler=tools.aiops_ping,
            description="Return a static pong payload for AIOps Hermes integration checks.",
        )

    return ["aiops_ping"]


def register_bot_commands(ctx: Any | None = None) -> list[str]:
    """Register the Task 0 CLI/bot command surface when a context is present.

    Hermes currently exposes plugin CLI registration via ``ctx.register_cli_command``.
    Task 0 does not add a live handler yet, but the skill path is surfaced so the
    VM-side Hermes runtime can inspect the packaged skill bundle.

    Args:
        ctx: Hermes plugin context.

    Returns:
        Relative skill bundle paths exposed by the plugin.
    """
    skill_path = Path(__file__).resolve().parent.parent / "bot" / "skills" / "aiops-ping" / "SKILL.md"
    if ctx is not None and hasattr(ctx, "register_cli_command"):
        # Task 0 only proves the command registration surface exists.
        ctx.register_cli_command(
            name="aiops",
            help="AIOps plugin management commands.",
            setup_fn=lambda parser: parser,
            handler_fn=lambda args: args,
        )

    return [str(skill_path)]
