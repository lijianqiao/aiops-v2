"""Stub async handlers backing the `/approval` bot command."""

from __future__ import annotations

from typing import Any


async def signal(args: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Return a placeholder approval response for Task 5."""
    del args, kwargs
    return {"message": "approval signaling lands in Task 10", "data": {"available": False}}
