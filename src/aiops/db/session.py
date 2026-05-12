"""Async SQLAlchemy engine and session factory helpers.

SQLAlchemy ``AsyncEngine`` instances are heavy (connection pools, TLS
contexts, metadata caches), so the entire process shares a single engine
and re-binds session factories to it. Passing a :class:`ResourceRegistry`
to :func:`get_engine` or :func:`create_session_factory` registers the
shared :func:`dispose_engine` closer so application shutdown drains the
pool gracefully (architecture §16.8 lifecycle pattern).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from aiops.lifecycle import ResourceRegistry
from aiops.settings import Settings

_engine: AsyncEngine | None = None


def get_engine(settings: Settings, *, registry: ResourceRegistry | None = None) -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use.

    Args:
        settings: Application settings carrying the SQLAlchemy database URL.
        registry: Optional resource registry. When provided on first
            engine creation, ``dispose_engine`` is registered as a
            shutdown closer.

    Returns:
        The shared :class:`AsyncEngine` instance.
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
        if registry is not None:
            registry.register("db_engine", dispose_engine)
    return _engine


def create_session_factory(
    settings: Settings, *, registry: ResourceRegistry | None = None
) -> async_sessionmaker[AsyncSession]:
    """Build an async session factory bound to the shared engine.

    Args:
        settings: Application settings carrying the database URL.
        registry: Optional resource registry forwarded to
            :func:`get_engine` so the engine's lifecycle is tracked.

    Returns:
        Async session factory bound to the process-wide engine.
    """
    return async_sessionmaker(bind=get_engine(settings, registry=registry), expire_on_commit=False)


async def dispose_engine() -> None:
    """Dispose the process-wide engine and clear the cache.

    Safe to call multiple times. Intended for application shutdown
    hooks (so the connection pool drains gracefully) and async test
    fixtures that need a clean slate between scenarios.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
