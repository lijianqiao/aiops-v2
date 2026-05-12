"""Application bootstrap for the AIOps project."""

from __future__ import annotations

from dataclasses import dataclass

from aiops.logging import configure_logging
from aiops.settings import Settings


@dataclass(slots=True)
class AppContainer:
    """Top-level application container.

    Attributes:
        settings: Runtime settings used by the process.
    """

    settings: Settings


def build_app() -> AppContainer:
    """Build the initial application container.

    Side effects:
        Configures ``structlog`` + stdlib ``logging`` to emit JSON to stdout
        before the rest of the process starts producing logs. The
        configuration is idempotent — safe to call from tests or repeated
        bootstrap paths.
    """
    configure_logging()
    return AppContainer(settings=Settings())


def main() -> None:
    """Run the bootstrap entrypoint."""
    print(f"{build_app().settings.app_name} bootstrap ready")
