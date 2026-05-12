"""Seed a local NetBox instance with development devices for Task 6."""

from __future__ import annotations

import time
from typing import Any, cast

import httpx
import pynetbox  # type: ignore[import-untyped]

from aiops.settings import Settings


def _wait_for_netbox(base_url: str, timeout_sec: float = 180.0) -> None:
    """Wait until NetBox responds to the login page health probe."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url.rstrip('/')}/login/", timeout=5.0)
            if response.status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    raise RuntimeError(f"NetBox at {base_url!r} did not become ready within {timeout_sec} seconds")


def _ensure_custom_field(base_url: str, token: str) -> None:
    """Ensure the `criticality` custom field exists for dcim.device."""
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=15.0, headers=headers) as client:
        response = client.get("/api/extras/custom-fields/", params={"name": "criticality"})
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return

        create_response = client.post(
            "/api/extras/custom-fields/",
            json={
                "name": "criticality",
                "label": "Criticality",
                "type": "text",
                "object_types": ["dcim.device"],
                "required": False,
            },
        )
        create_response.raise_for_status()


def _get_or_create(endpoint: Any, **kwargs: object) -> Any:
    """Get an object by slug or name, creating it if absent."""
    slug = kwargs.get("slug")
    name = kwargs.get("name")
    existing = None
    if slug is not None and hasattr(endpoint, "get"):
        existing = endpoint.get(slug=slug)
    if existing is None and name is not None and hasattr(endpoint, "get"):
        existing = endpoint.get(name=name)
    if existing is not None:
        return existing
    return endpoint.create(**kwargs)


def main() -> None:
    """Seed NetBox with a deterministic set of development devices."""
    settings = Settings()
    token = settings.netbox_token.get_secret_value() or "netbox-token"

    _wait_for_netbox(settings.netbox_url)
    _ensure_custom_field(settings.netbox_url, token)

    nb: Any = pynetbox.api(settings.netbox_url, token=token)

    site = cast(Any, _get_or_create(nb.dcim.sites, name="Lab Site", slug="lab-site", status="active"))

    manufacturer_h3c = cast(Any, _get_or_create(nb.dcim.manufacturers, name="H3C", slug="h3c"))
    manufacturer_huawei = cast(Any, _get_or_create(nb.dcim.manufacturers, name="Huawei", slug="huawei"))
    manufacturer_linux = cast(Any, _get_or_create(nb.dcim.manufacturers, name="Linux", slug="linux"))

    role_access = cast(Any, _get_or_create(nb.dcim.device_roles, name="Access", slug="access", color="4caf50"))
    role_aggregation = cast(
        Any, _get_or_create(nb.dcim.device_roles, name="Aggregation", slug="aggregation", color="ff9800")
    )
    role_core = cast(Any, _get_or_create(nb.dcim.device_roles, name="Core", slug="core", color="f44336"))
    role_server = cast(Any, _get_or_create(nb.dcim.device_roles, name="Server", slug="server", color="2196f3"))

    access_type = cast(
        Any,
        _get_or_create(
            nb.dcim.device_types,
            manufacturer=manufacturer_h3c.id,
            model="H3C Access Switch",
            slug="h3c-access-switch",
        ),
    )
    aggregation_type = cast(
        Any,
        _get_or_create(
            nb.dcim.device_types,
            manufacturer=manufacturer_h3c.id,
            model="H3C Aggregation Switch",
            slug="h3c-aggregation-switch",
        ),
    )
    core_type = cast(
        Any,
        _get_or_create(
            nb.dcim.device_types,
            manufacturer=manufacturer_huawei.id,
            model="Huawei Core Switch",
            slug="huawei-core-switch",
        ),
    )
    server_type = cast(
        Any,
        _get_or_create(
            nb.dcim.device_types,
            manufacturer=manufacturer_linux.id,
            model="Linux Server",
            slug="linux-server",
        ),
    )

    devices = [
        ("access-sw-01", access_type.id, role_access.id, "medium"),
        ("access-sw-02", access_type.id, role_access.id, "medium"),
        ("access-sw-03", access_type.id, role_access.id, "medium"),
        ("access-sw-04", access_type.id, role_access.id, "medium"),
        ("agg-sw-01", aggregation_type.id, role_aggregation.id, "high"),
        ("agg-sw-02", aggregation_type.id, role_aggregation.id, "high"),
        ("core-sw-01", core_type.id, role_core.id, "critical"),
        ("core-sw-02", core_type.id, role_core.id, "critical"),
        ("host-a", server_type.id, role_server.id, "medium"),
        ("host-b", server_type.id, role_server.id, "medium"),
    ]

    for name, device_type_id, role_id, criticality in devices:
        existing = nb.dcim.devices.get(name=name)
        payload = {
            "name": name,
            "device_type": device_type_id,
            "role": role_id,
            "site": site.id,
            "status": "active",
            "custom_fields": {"criticality": criticality},
        }
        if existing is None:
            nb.dcim.devices.create(**payload)
        else:
            existing.update(payload)


if __name__ == "__main__":
    main()
