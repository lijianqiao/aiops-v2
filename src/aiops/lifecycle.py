"""Process-wide async resource shutdown registry.

The control plane accumulates several heavy async resources during boot
(SQLAlchemy engine, Redis pool, httpx client, future Scrapli sessions,
Temporal client, Langfuse SDK). Each must be closed gracefully when the
process shuts down or a test fixture tears the harness down.

``build_app`` constructs a :class:`ResourceRegistry`, attaches it to the
returned :class:`AppContainer`, and publishes it via
:func:`set_global_registry` so plugin-loaded code (Hermes hooks, gateway
service bundles) that has no direct access to the container can still
register their close callables.

Shutdown order is LIFO so resources created later — and therefore likely
to depend on earlier ones — are closed first. Errors from individual
closers are logged and swallowed so a single broken resource cannot
block the rest of the chain.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog

CloserCallable = Callable[[], Awaitable[None]]


class ResourceRegistry:
    """Ordered async resource shutdown registry.

    Attributes:
        registered: Names of all currently-registered (not yet closed) resources.
    """

    def __init__(self) -> None:
        self._closers: list[tuple[str, CloserCallable]] = []
        self._closed: bool = False

    def register(self, name: str, closer: CloserCallable) -> None:
        """Register an async close callable under ``name``.

        Args:
            name: Human-readable identifier used in shutdown audit logs.
            closer: Async no-arg callable responsible for releasing the resource.

        Raises:
            RuntimeError: If the registry has already been closed.
        """
        if self._closed:
            raise RuntimeError(f"cannot register {name!r} after registry was closed")
        self._closers.append((name, closer))

    async def aclose(self) -> None:
        """Close every registered resource in LIFO order.

        Errors from individual closers are logged and swallowed so one
        broken resource cannot block the rest of the shutdown chain.
        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._closed:
            return

        log = structlog.get_logger()
        for name, closer in reversed(self._closers):
            try:
                await closer()
            except Exception as error:  # noqa: BLE001
                log.error("resource_close_failed", resource=name, error=str(error))
        self._closers.clear()
        self._closed = True

    @property
    def registered(self) -> list[str]:
        """Names of currently-registered resources, in registration order."""
        return [name for name, _ in self._closers]


_global_registry: ResourceRegistry | None = None


def get_global_registry() -> ResourceRegistry:
    """Return the process-wide registry, creating one on first use.

    Plugin code (Hermes hooks, gateway service bundles) cannot reach the
    ``AppContainer`` directly, so it consults this accessor to register
    its async close callables.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ResourceRegistry()
    return _global_registry


def set_global_registry(registry: ResourceRegistry) -> None:
    """Publish a registry as the process-wide singleton.

    ``build_app`` calls this with the registry it attaches to the
    returned :class:`AppContainer` so plugin-loaded code shares the same
    shutdown chain as the explicit application bootstrap.
    """
    global _global_registry
    _global_registry = registry


async def shutdown() -> None:
    """Close the process-wide registry if one has been published."""
    if _global_registry is not None:
        await _global_registry.aclose()
