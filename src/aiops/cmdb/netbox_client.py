"""NetBox client abstractions used by webhook and policy layers."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from aiops.settings import Settings


@dataclass(slots=True)
class NetBoxDevice:
    """Minimal device projection returned by the NetBox client.

    Attributes:
        name: Device name in NetBox.
        role: Device role such as access, aggregation, or core.
        manufacturer: Vendor name used for driver selection.
        interfaces: Known interface names for early validation hooks.
    """

    name: str
    role: str
    manufacturer: str
    interfaces: list[str] = field(default_factory=list)


class NetBoxClient:
    """Mock-friendly async NetBox client stub.

    The real HTTP implementation lands later. Task 4 only needs a stable
    async interface for unit tests and webhook orchestration.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        """Initialize the NetBox client.

        Args:
            settings: Application settings carrying NetBox endpoint and token.
            client: Optional injected HTTP client for tests.
        """
        self._base_url = settings.netbox_url.rstrip("/")
        self._token = settings.netbox_token.get_secret_value()
        self._client = client or httpx.AsyncClient(base_url=self._base_url, timeout=10.0)

    async def get_device(self, device_name: str) -> NetBoxDevice | None:
        """Look up a device by name.

        Args:
            device_name: Host or device name from the incoming alert payload.

        Returns:
            The matching NetBox device, or ``None`` when no device exists.
        """
        if not self._token:
            return None

        response = await self._client.get(
            "/api/dcim/devices/",
            params={"name": device_name},
            headers={"Authorization": f"Token {self._token}"},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return None

        device = results[0]
        role = device.get("role", {}).get("slug") or device.get("role", {}).get("name") or "unknown"
        manufacturer = (
            device.get("device_type", {}).get("manufacturer", {}).get("slug")
            or device.get("device_type", {}).get("manufacturer", {}).get("name")
            or "unknown"
        )
        return NetBoxDevice(
            name=device.get("name", device_name),
            role=role,
            manufacturer=manufacturer,
            interfaces=[],
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client.

        Safe to call once and only once per client instance. Subsequent
        calls are no-ops via ``httpx.AsyncClient.aclose`` semantics.
        Wired into the application :class:`ResourceRegistry` by
        :func:`aiops.gateway.services.build_service_bundle` so process
        shutdown drains the connection pool gracefully.
        """
        await self._client.aclose()
