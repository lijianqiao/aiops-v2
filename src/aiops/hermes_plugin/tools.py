"""Minimal Hermes tool handlers used for Task 0 boundary probing."""

from __future__ import annotations

import json
from typing import Any

PING_TOOL_SCHEMA: dict[str, Any] = {
    "name": "aiops_ping",
    "description": "Return a static health response for AIOps Hermes integration checks.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Optional text to echo back with the pong response.",
            }
        },
        "required": [],
    },
}


def aiops_ping(params: dict[str, Any] | None = None, **_: Any) -> str:
    """Return a stable JSON payload for connectivity checks.

    Args:
        params: Optional tool parameters from Hermes.

    Returns:
        JSON string containing the pong response payload.
    """
    message = "pong"
    if params and isinstance(params.get("message"), str):
        message = f"pong: {params['message']}"

    return json.dumps({"success": True, "message": message})
