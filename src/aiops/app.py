"""Application bootstrap for the AIOps project."""

from __future__ import annotations

from dataclasses import dataclass, field

from aiops.lifecycle import ResourceRegistry, set_global_registry
from aiops.logging import configure_logging
from aiops.settings import Settings


@dataclass(slots=True)
class AppContainer:
    """Top-level application container.

    Attributes:
        settings: Runtime settings used by the process.
        resources: Process-wide async resource shutdown registry. Plugin
            code reaches the same registry via
            :func:`aiops.lifecycle.get_global_registry`.
    """

    settings: Settings
    resources: ResourceRegistry = field(default_factory=ResourceRegistry)


def build_app() -> AppContainer:
    """Build the initial application container.

    Side effects:
        - Configures ``structlog`` + stdlib ``logging`` to emit JSON to
          stdout. Idempotent.
        - Publishes the container's :class:`ResourceRegistry` as the
          process-wide singleton via :func:`set_global_registry` so
          Hermes-loaded plugin code can register shutdown closers
          without reaching the :class:`AppContainer` directly.
    """
    configure_logging()
    container = AppContainer(settings=Settings())
    set_global_registry(container.resources)
    return container


def main() -> None:
    """Run the bootstrap entrypoint."""
    print(f"{build_app().settings.app_name} bootstrap ready")
