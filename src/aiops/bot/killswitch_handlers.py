"""Stub async handlers backing the `/kill-switch` bot command."""

from __future__ import annotations

from typing import Any


async def dispatch(args: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Return a placeholder kill-switch response for Task 5."""
    del args, kwargs
    return {"message": "kill-switch operations land in Task 8", "data": {"available": False}}
