"""Operator command-line entrypoint for the AIOps platform.

Wired in ``pyproject.toml`` as the ``aiops-cli`` console script. Currently
exposes the root group only; later tasks attach subcommands via
``@main.command()`` without breaking the existing invocation contract:

- ``approval signal <workflow_id> approve|reject`` — Task 10
- ``kill-switch on|off|list`` — Task 10
- ``memory purge --trace=<id>`` — Task 11
- ``eval run --dataset=<id>`` — Task 11
"""

from __future__ import annotations

import click

from aiops.app import build_app


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Run the AIOps operator CLI.

    With no subcommand the script prints a bootstrap line so it doubles as a
    Task 1 sanity check (matches ``python main.py``). Once subcommands land
    in Tasks 10 / 11 this becomes the standard Click dispatch flow.

    Args:
        ctx: Click execution context used to detect whether a subcommand
            was invoked.
    """
    if ctx.invoked_subcommand is None:
        click.echo(f"{build_app().settings.app_name} cli bootstrap ready")
