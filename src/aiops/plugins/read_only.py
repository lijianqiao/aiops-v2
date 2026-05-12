"""Read-only Hermes tool handlers for Linux and network triage.

Each handler obeys the Hermes tool contract (§5.5.5): receive ``args`` +
``**kwargs``, return a JSON string, never raise. Handlers consume their
transport from ``kwargs["transport"]`` rather than constructing a fresh
connection — the production wrapper (Task 9) attaches the pooled
:class:`LinuxTransport` or :class:`NetworkTransport` before invoking the
handler.

``host`` and ``command`` are always passed to the transport as distinct
arguments. The transport, not this module, is responsible for connecting
to the host safely; we never concatenate ``host`` into a shell string.
"""

from __future__ import annotations

import json
from typing import Any

from aiops.plugins.transports import LinuxTransport, NetworkTransport

GET_DISK_USAGE_SCHEMA: dict[str, Any] = {
    "name": "get_disk_usage",
    "description": "Read df -h output on a Linux host. Returns array of mount points.",
    "parameters": {
        "type": "object",
        "properties": {"host": {"type": "string", "description": "Hostname in NetBox"}},
        "required": ["host"],
    },
}

GET_SYSTEMD_STATUS_SCHEMA: dict[str, Any] = {
    "name": "get_systemd_status",
    "description": "Read systemd unit status on a Linux host.",
    "parameters": {
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Hostname in NetBox"},
            "service": {"type": "string", "description": "systemd unit name"},
        },
        "required": ["host", "service"],
    },
}

GET_INTERFACE_STATUS_SCHEMA: dict[str, Any] = {
    "name": "get_interface_status",
    "description": "Read interface counters and state from a network device.",
    "parameters": {
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Network device name in NetBox"},
            "interface": {"type": "string", "description": "Interface name"},
        },
        "required": ["host", "interface"],
    },
}

GET_OSPF_NEIGHBORS_SCHEMA: dict[str, Any] = {
    "name": "get_ospf_neighbors",
    "description": "Read OSPF neighbor status from a network device.",
    "parameters": {
        "type": "object",
        "properties": {"host": {"type": "string", "description": "Network device name in NetBox"}},
        "required": ["host"],
    },
}


def _missing_arg(error: KeyError) -> str:
    """Render a missing-argument error in the Hermes JSON contract."""
    return json.dumps({"ok": False, "error": f"missing arg: {error.args[0]}"})


def _parse_df_h(output: str) -> list[dict[str, str]]:
    """Parse ``df -h`` output into structured rows."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = line.split(maxsplit=5)
        if len(parts) != 6:
            continue
        rows.append(
            {
                "filesystem": parts[0],
                "size": parts[1],
                "used": parts[2],
                "available": parts[3],
                "use_pct": parts[4],
                "mountpoint": parts[5],
            }
        )
    return rows


def _parse_key_value_output(output: str) -> dict[str, str]:
    """Parse simple ``key=value`` command output."""
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        parsed[key.strip().lower()] = value.strip()
    return parsed


def _parse_ospf_neighbors(output: str) -> list[dict[str, str]]:
    """Parse simplified OSPF neighbor output."""
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        rows.append({"neighbor_id": parts[0], "state": parts[1], "interface": parts[2]})
    return rows


async def get_disk_usage(args: dict[str, Any], **kwargs: Any) -> str:
    """Return normalized ``df -h`` rows in Hermes JSON-string format.

    Requires ``kwargs["transport"]`` to satisfy :class:`LinuxTransport`.
    """
    try:
        host = args["host"]
        transport: LinuxTransport = kwargs["transport"]
        output = await transport.run(host, "df -h")
        return json.dumps({"ok": True, "rows": _parse_df_h(output)})
    except KeyError as error:
        return _missing_arg(error)
    except Exception as error:  # noqa: BLE001
        return json.dumps({"ok": False, "error": str(error)})


async def get_systemd_status(args: dict[str, Any], **kwargs: Any) -> str:
    """Return normalized systemd status in Hermes JSON-string format.

    Requires ``kwargs["transport"]`` to satisfy :class:`LinuxTransport`.
    """
    try:
        host = args["host"]
        service = args["service"]
        transport: LinuxTransport = kwargs["transport"]
        command = f"systemctl show {service} --no-page --property=Id,LoadState,ActiveState,SubState"
        status = _parse_key_value_output(await transport.run(host, command))
        return json.dumps({"ok": True, "status": status})
    except KeyError as error:
        return _missing_arg(error)
    except Exception as error:  # noqa: BLE001
        return json.dumps({"ok": False, "error": str(error)})


async def get_interface_status(args: dict[str, Any], **kwargs: Any) -> str:
    """Return simplified interface status from a network device.

    Requires ``kwargs["transport"]`` to satisfy :class:`NetworkTransport`.
    """
    try:
        host = args["host"]
        interface = args["interface"]
        transport: NetworkTransport = kwargs["transport"]
        output = await transport.send_command(host, f"display interface {interface}")
        return json.dumps({"ok": True, "interface": interface, "output": output})
    except KeyError as error:
        return _missing_arg(error)
    except Exception as error:  # noqa: BLE001
        return json.dumps({"ok": False, "error": str(error)})


async def get_ospf_neighbors(args: dict[str, Any], **kwargs: Any) -> str:
    """Return normalized OSPF neighbor rows from a network device.

    Requires ``kwargs["transport"]`` to satisfy :class:`NetworkTransport`.
    """
    try:
        host = args["host"]
        transport: NetworkTransport = kwargs["transport"]
        output = await transport.send_command(host, "display ospf peer")
        return json.dumps({"ok": True, "rows": _parse_ospf_neighbors(output)})
    except KeyError as error:
        return _missing_arg(error)
    except Exception as error:  # noqa: BLE001
        return json.dumps({"ok": False, "error": str(error)})
