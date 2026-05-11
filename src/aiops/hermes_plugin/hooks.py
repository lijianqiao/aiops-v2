"""Minimal Hermes hook callbacks used for Task 0 boundary probing."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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
