"""Async handlers backing the `/incident` bot command."""

from __future__ import annotations

from typing import Any


async def dispatch(args: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Handle basic incident queries with a pure async dict result."""
    del kwargs
    incident_id = args.get("incident_id")
    if incident_id:
        return {
            "message": f"incident {incident_id} is not available yet",
            "data": {"incident_id": incident_id, "status": "unknown"},
        }
    return {
        "message": "incident listing is wired; backing data source lands in a later task",
        "data": {"items": [], "count": 0},
    }
