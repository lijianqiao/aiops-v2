"""Bot command registration for the Hermes gateway role."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from aiops.bot import approval_handlers, cost_handlers, incident_handlers, killswitch_handlers, wiki_handlers

CommandHandler = Callable[..., Awaitable[dict[str, Any]]]


def _handler(function: CommandHandler) -> Callable[..., Awaitable[str]]:
    """Wrap async handlers so they always return JSON strings.

    The wrapper catches every exception, emits a structured log line
    (so operators see failures even when the user only sees the JSON
    envelope), and surfaces the error via ``{"ok": False, "error": ...}``
    per the Hermes tool contract (§5.5.5).
    """

    async def wrapped(args: dict[str, Any], **kwargs: Any) -> str:
        try:
            data = await function(args, **kwargs)
            return json.dumps({"ok": True, **data})
        except Exception as error:  # noqa: BLE001
            structlog.get_logger().error(
                "bot_command_failed",
                handler=function.__qualname__,
                error=str(error),
            )
            return json.dumps({"ok": False, "error": str(error)})

    return wrapped


def register_bot_commands(ctx: Any) -> None:
    """Register gateway bot slash commands."""
    ctx.register_command(
        name="incident",
        handler=_handler(incident_handlers.dispatch),
        description="Query incidents: /incident list | /incident <id>",
    )
    ctx.register_command(
        name="wiki",
        handler=_handler(wiki_handlers.search),
        description="Search wiki: /wiki search <kw>",
    )
    ctx.register_command(
        name="cost",
        handler=_handler(cost_handlers.report),
        description="Cost report: /cost report [--today]",
    )
    ctx.register_command(
        name="kill-switch",
        handler=_handler(killswitch_handlers.dispatch),
        description="Kill switch ops",
    )
    ctx.register_command(
        name="approval",
        handler=_handler(approval_handlers.signal),
        description="Manual approval signal (degradation path)",
    )
