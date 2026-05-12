"""Transport protocols for Linux and network device tool handlers.

Linux hosts (asyncssh / paramiko) and network devices (Scrapli / NAPALM)
have different connection lifecycles and command-issue semantics. Each
:class:`Protocol` here pins the *minimum* contract a tool handler needs
so Task 9 can swap in real production wrappers without touching any
handler body.

Both contracts keep ``host`` and ``command`` as **distinct arguments**.
This is deliberate: a single ``transport.run("ssh host cmd")`` shape
would invite shell-string concatenation of LLM-controlled ``host`` values
and re-introduce the injection surface that architecture §12 explicitly
forbids. asyncssh connects to a host first and then runs commands on the
open channel; Scrapli takes ``host`` at construction time and
``send_command`` only receives commands.
"""

from __future__ import annotations

from typing import Protocol


class LinuxTransport(Protocol):
    """asyncssh-compatible async SSH transport for Linux / Windows hosts.

    Production implementations typically wrap a connection pool keyed by
    ``host`` and dispatch the command on the matching channel.
    """

    async def run(self, host: str, command: str) -> str: ...


class NetworkTransport(Protocol):
    """Scrapli-compatible async transport for network devices.

    Production implementations resolve the platform driver
    (``hp_comware`` / ``huawei_vrp`` / ``cisco_iosxe``) from NetBox
    metadata before issuing ``send_command``.
    """

    async def send_command(self, host: str, command: str) -> str: ...
