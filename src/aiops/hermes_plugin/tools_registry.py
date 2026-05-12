"""Role-specific Hermes tool registration."""

from __future__ import annotations

from typing import Any

from aiops.plugins import read_only


def register_linux_tools(ctx: Any) -> None:
    """Register Linux read-only tools."""
    ctx.register_tool(
        name="get_disk_usage",
        toolset="aiops",
        schema=read_only.GET_DISK_USAGE_SCHEMA,
        handler=read_only.get_disk_usage,
        description="Read df -h output on a Linux host.",
    )
    ctx.register_tool(
        name="get_systemd_status",
        toolset="aiops",
        schema=read_only.GET_SYSTEMD_STATUS_SCHEMA,
        handler=read_only.get_systemd_status,
        description="Read systemd unit status on a Linux host.",
    )


def register_network_tools(ctx: Any) -> None:
    """Register network read-only tools."""
    ctx.register_tool(
        name="get_interface_status",
        toolset="aiops",
        schema=read_only.GET_INTERFACE_STATUS_SCHEMA,
        handler=read_only.get_interface_status,
        description="Read interface status from a network device.",
    )
    ctx.register_tool(
        name="get_ospf_neighbors",
        toolset="aiops",
        schema=read_only.GET_OSPF_NEIGHBORS_SCHEMA,
        handler=read_only.get_ospf_neighbors,
        description="Read OSPF neighbor state from a network device.",
    )


def register_infra_tools(ctx: Any) -> None:
    """Register infra role tools.

    Task 5 does not require infra-specific handlers yet, so the function is a
    no-op placeholder that preserves the role-dispatch boundary.
    """
    del ctx
