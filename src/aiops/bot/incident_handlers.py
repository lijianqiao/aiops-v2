"""Async handlers backing the ``/incident`` bot command.

**Phase 1 limitation**: the underlying ``alerts`` table only carries the
upstream ``source_event_id`` (Zabbix ``eventid``). Incident aggregation
and the platform-internal display identifier (``INC-...``) land in a
later task. Until then this handler treats every user-supplied
identifier as a ``source_event_id`` and surfaces alerts (not aggregated
incidents) one-for-one.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from aiops.contracts.bot import BotCard
from aiops.db.repositories import AlertRepository
from aiops.db.session import create_session_factory
from aiops.settings import Settings

_LAST_WINDOW_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[mh])$")
_LIMIT_DEFAULT = 20
_LIMIT_MAX = 100


@lru_cache(maxsize=1)
def _session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory used by incident queries.

    Wrapped in ``lru_cache`` so the handler does not rebuild ``Settings``
    and the SQLAlchemy sessionmaker on every command invocation. The
    underlying engine is shared via :func:`aiops.db.session.get_engine`
    so even before this cache only the wrapper was new — but reading
    ``Settings()`` on every call is still measurable.

    Tests monkeypatch this function to inject a mock factory instead of
    standing up real Postgres.
    """
    return create_session_factory(Settings())


def _parse_last_window(raw: str | None) -> datetime | None:
    """Parse a simple relative time window like ``5m`` or ``2h``."""
    if raw is None:
        return None

    match = _LAST_WINDOW_PATTERN.fullmatch(raw.strip())
    if match is None:
        raise ValueError(f"unsupported time window: {raw!r}")

    value = int(match.group("value"))
    unit = match.group("unit")
    delta = timedelta(minutes=value) if unit == "m" else timedelta(hours=value)
    return datetime.now(UTC) - delta


def _clamp_limit(raw: Any) -> int:
    """Clamp the user-supplied ``limit`` to ``[1, _LIMIT_MAX]``.

    LLM-supplied arguments are untrusted; without a hard upper bound a
    rogue ``limit=10_000_000`` would happily try to materialize ten
    million rows into memory before the wrapper formats the response.

    Bool values are excluded explicitly because ``bool`` is an ``int``
    subclass in Python — ``limit=True`` would otherwise pass through as 1.
    """
    if raw is None or isinstance(raw, bool):
        return _LIMIT_DEFAULT
    if isinstance(raw, int):
        return max(1, min(raw, _LIMIT_MAX))
    if isinstance(raw, str):
        text = raw.strip()
        if text.lstrip("-").isdigit():
            return max(1, min(int(text), _LIMIT_MAX))
    return _LIMIT_DEFAULT


async def _list_recent_alerts(*, last: str | None, limit: int) -> list[BotCard]:
    """Load recent alerts from Postgres and convert them into Bot cards."""
    async with _session_factory()() as session:
        repository = AlertRepository(session)
        alerts = await repository.list_recent(since=_parse_last_window(last), limit=limit)

    cards: list[BotCard] = []
    for alert in alerts:
        cards.append(
            BotCard(
                title=alert.trigger_name or alert.source_event_id,
                body=(
                    f"event={alert.source_event_id} host={alert.host or '-'} "
                    f"risk={alert.risk_level or '-'} route={alert.route_name or '-'}"
                ),
                metadata={
                    "source_event_id": alert.source_event_id,
                    "host": alert.host,
                    "risk_level": alert.risk_level,
                },
            )
        )
    return cards


async def _get_alert_card(source_event_id: str) -> BotCard | None:
    """Return one alert card by its upstream ``source_event_id``."""
    async with _session_factory()() as session:
        repository = AlertRepository(session)
        alert = await repository.get_by_source_event_id(source_event_id)

    if alert is None:
        return None
    return BotCard(
        title=alert.trigger_name or source_event_id,
        body=f"event={alert.source_event_id} host={alert.host or '-'} risk={alert.risk_level or '-'}",
        metadata={"source_event_id": alert.source_event_id, "route_name": alert.route_name},
    )


async def dispatch(args: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Handle alert queries against the persisted alert table.

    Args:
        args: Command arguments.
            - ``source_event_id`` / ``event_id``: single-alert lookup by
              upstream event id.
            - ``last``: relative time window (``5m`` / ``2h``); applies
              to the list path only.
            - ``limit``: max rows for the list path, clamped to
              ``[1, 100]``.

    Returns:
        Dict carrying ``message``, ``cards``, and ``data``. The handler
        never raises — the wrapping JSON envelope in
        :mod:`aiops.hermes_plugin.commands_registry` handles error paths.
    """
    del kwargs
    source_event_id = str(args.get("source_event_id") or args.get("event_id") or "").strip()
    if source_event_id:
        card = await _get_alert_card(source_event_id)
        if card is None:
            return {
                "message": f"no alert found for event_id={source_event_id}",
                "cards": [],
                "data": {"source_event_id": source_event_id, "status": "missing"},
            }
        return {
            "message": f"alert {source_event_id} loaded",
            "cards": [card.model_dump()],
            "data": {"source_event_id": source_event_id, "status": "loaded"},
        }

    limit = _clamp_limit(args.get("limit"))
    cards = await _list_recent_alerts(last=args.get("last"), limit=limit)
    return {
        "message": f"loaded {len(cards)} recent alert(s)",
        "cards": [card.model_dump() for card in cards],
        "data": {"count": len(cards), "limit": limit},
    }
