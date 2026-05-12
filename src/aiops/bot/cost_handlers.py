"""Async handlers backing the `/cost` bot command."""

from __future__ import annotations

from typing import Any


async def report(args: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Return a placeholder cost summary until ledger reporting lands."""
    del kwargs
    today = bool(args.get("today"))
    window = "today" if today else "all"
    return {
        "message": f"cost reporting is seeded for window={window}",
        "data": {"window": window, "total_usd": 0.0},
    }
