"""Async handlers backing the ``/wiki`` bot command."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


def _wiki_root() -> Path:
    """Return the repository wiki directory."""
    return Path(__file__).resolve().parents[3] / "wiki"


def _scan_wiki_blocking(keyword: str) -> list[dict[str, str]]:
    """Synchronously scan the wiki tree for keyword matches.

    Factored into a helper so the async ``search`` coroutine can offload
    the blocking filesystem walk to a worker thread via
    :func:`asyncio.to_thread` — important once the wiki grows beyond a
    handful of seed files.
    """
    matches: list[dict[str, str]] = []
    root = _wiki_root()
    for path in sorted(root.rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        if keyword.lower() in content.lower():
            matches.append({"path": str(path.relative_to(root)), "title": path.stem})
    return matches


async def search(args: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Search seeded wiki markdown files by keyword."""
    del kwargs
    keyword = str(args.get("keyword") or args.get("query") or "").strip()
    if not keyword:
        return {"message": "wiki search requires a keyword", "data": {"matches": []}}

    matches = await asyncio.to_thread(_scan_wiki_blocking, keyword)

    return {
        "message": f"wiki search returned {len(matches)} match(es)",
        "data": {"keyword": keyword, "matches": matches},
    }
