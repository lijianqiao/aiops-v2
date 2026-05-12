"""Async SQLAlchemy engine and session factory helpers.

SQLAlchemy ``AsyncEngine`` instances are heavy (connection pools, TLS
contexts, metadata caches), so the entire process shares a single engine
and re-binds session factories to it. ``dispose_engine`` is provided so
application shutdown hooks and test fixtures can shut the pool down
cleanly without leaking connections.

This module purposely avoids importing the engine eagerly: ``get_engine``
is called only when the first session factory is requested, which keeps
Task 0-2 unit tests free of any database dependency.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from aiops.settings import Settings

_engine: AsyncEngine | None = None


def get_engine(settings: Settings) -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use.

    Subsequent calls return the cached instance regardless of the
    ``settings`` argument, which prevents callers from accidentally
    creating multiple connection pools against the same database URL.

    Args:
        settings: Application settings carrying the SQLAlchemy database URL.

    Returns:
        The shared :class:`AsyncEngine` instance.
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
    return _engine


def create_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Build an async session factory bound to the shared engine.

    Args:
        settings: Application settings carrying the database URL.

    Returns:
        Async session factory bound to the process-wide engine returned by
        :func:`get_engine`.
    """
    return async_sessionmaker(bind=get_engine(settings), expire_on_commit=False)


async def dispose_engine() -> None:
    """Dispose the process-wide engine and clear the cache.

    Safe to call multiple times. Intended for application shutdown hooks
    (so the connection pool drains gracefully) and async test fixtures
    that need a clean slate between scenarios.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
