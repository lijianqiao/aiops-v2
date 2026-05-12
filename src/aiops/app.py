"""Application bootstrap for the AIOps project."""

from __future__ import annotations

from dataclasses import dataclass

from aiops.settings import Settings


@dataclass(slots=True)
class AppContainer:
    """Top-level application container.

    Attributes:
        settings: Runtime settings used by the process.
    """

    settings: Settings


def build_app() -> AppContainer:
    """Build the initial application container."""
    return AppContainer(settings=Settings())


def main() -> None:
    """Run the bootstrap entrypoint."""
    print(f"{build_app().settings.app_name} bootstrap ready")
