"""Service bundle assembly for gateway webhook handlers.

The runtime service bundle wires the DB facade, Redis client, and NetBox
client used by :func:`aiops.gateway.hooks.dedupe_and_persist`. Tests
inject typed mocks via :func:`build_services`; production code uses
:func:`build_service_bundle` which caches the bundle process-wide and
registers every owned async resource on the
:class:`aiops.lifecycle.ResourceRegistry` so shutdown drains pools
gracefully (architecture §16.8 lifecycle pattern).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from redis.asyncio import Redis

from aiops.cmdb.netbox_client import NetBoxClient, NetBoxDevice
from aiops.db.repositories import AlertRepository
from aiops.db.session import create_session_factory
from aiops.lifecycle import ResourceRegistry, get_global_registry
from aiops.settings import Settings


class GatewayDb(Protocol):
    """Database facade contract used by gateway webhook hooks."""

    async def alert_exists(self, source_event_id: str) -> bool: ...

    async def get_cached_result(self, source_event_id: str) -> dict[str, Any]: ...

    async def insert_alert(
        self,
        *,
        source_event_id: str,
        route_name: str,
        host: str | None,
        trigger_name: str | None,
        risk_level: str,
        severity: str | None,
        raw_payload: dict[str, Any],
    ) -> dict[str, Any]: ...


class GatewayNetbox(Protocol):
    """NetBox facade contract used for device enrichment."""

    async def get_device(self, device_name: str) -> NetBoxDevice | None: ...


@dataclass(slots=True)
class GatewayServices:
    """Runtime services needed by gateway webhook hooks.

    Attributes:
        db: Persistence facade satisfying :class:`GatewayDb`.
        redis: Redis client (``redis.asyncio.Redis`` in production). Typed
            as ``Any`` because the redis-py async ``set`` signature surface
            is too broad — mirroring it in a Protocol would force every
            test mock to declare a dozen unused kwargs. Wire-level
            guarantees come from integration tests rather than the type
            system here.
        netbox: NetBox client satisfying :class:`GatewayNetbox`.
    """

    db: GatewayDb
    redis: Any
    netbox: GatewayNetbox


def build_services(*, db: GatewayDb, redis: Any, netbox: GatewayNetbox) -> GatewayServices:
    """Build a service bundle for tests and local orchestration.

    Args:
        db: Database facade satisfying :class:`GatewayDb`.
        redis: Redis client (``redis.asyncio.Redis`` or compatible).
        netbox: NetBox client satisfying :class:`GatewayNetbox`.
    """
    return GatewayServices(db=db, redis=redis, netbox=netbox)


@dataclass(slots=True)
class GatewayDatabase:
    """DB facade used by the gateway hook runtime.

    A fresh SQLAlchemy session is opened per call so Hermes hook
    invocations do not share transaction state across concurrent webhook
    deliveries.
    """

    session_factory: Any

    async def alert_exists(self, source_event_id: str) -> bool:
        """Return whether the alert already exists."""
        async with self.session_factory() as session:
            repository = AlertRepository(session)
            return await repository.alert_exists(source_event_id)

    async def get_cached_result(self, source_event_id: str) -> dict[str, Any]:
        """Return the cached raw payload for a previous alert."""
        async with self.session_factory() as session:
            repository = AlertRepository(session)
            return await repository.get_cached_result(source_event_id)

    async def insert_alert(
        self,
        *,
        source_event_id: str,
        route_name: str,
        host: str | None,
        trigger_name: str | None,
        risk_level: str,
        severity: str | None,
        raw_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist an inbound alert and return its raw payload."""
        async with self.session_factory() as session:
            async with session.begin():
                repository = AlertRepository(session)
                alert = await repository.insert_alert(
                    source_event_id=source_event_id,
                    source=route_name.split("_", maxsplit=1)[0],
                    route_name=route_name,
                    host=host,
                    trigger_name=trigger_name,
                    severity=severity,
                    risk_level=risk_level,
                    raw_payload=raw_payload,
                )
            return alert.raw_payload


_service_bundle: GatewayServices | None = None


async def build_service_bundle(
    settings: Settings | None = None,
    *,
    registry: ResourceRegistry | None = None,
) -> GatewayServices:
    """Build the live service bundle for Hermes webhook hooks.

    The bundle is cached process-wide. On first construction every owned
    async resource (Redis pool, NetBox httpx client, shared SQLAlchemy
    engine) is registered on the resource registry so application
    shutdown drains them in LIFO order.

    Args:
        settings: Application settings. Defaults to a freshly read instance.
        registry: Optional registry override. Defaults to the process-wide
            registry resolved via :func:`get_global_registry` so plugin
            code without ``AppContainer`` access still participates in
            orderly shutdown.

    Returns:
        Cached :class:`GatewayServices` instance.
    """
    global _service_bundle
    if _service_bundle is None:
        active_settings = settings or Settings()
        active_registry = registry if registry is not None else get_global_registry()

        session_factory = create_session_factory(active_settings, registry=active_registry)
        redis_client = Redis.from_url(active_settings.redis_url, decode_responses=True)
        netbox_client = NetBoxClient(active_settings)

        active_registry.register("gateway_redis", redis_client.aclose)
        active_registry.register("gateway_netbox", netbox_client.aclose)

        _service_bundle = GatewayServices(
            db=GatewayDatabase(session_factory=session_factory),
            redis=redis_client,
            netbox=netbox_client,
        )
    return _service_bundle


async def dispose_service_bundle() -> None:
    """Clear the cached service bundle so the next call rebuilds it.

    Resource shutdown is performed by the registered closers, not by this
    function. Use it from tests to reset state between scenarios.
    """
    global _service_bundle
    _service_bundle = None
