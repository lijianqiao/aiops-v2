"""Bootstrap settings stub for the AIOps platform.

Task 1 ships a minimal dataclass-backed settings object so the rest of the
bootstrap chain has something to import. Task 2 replaces this with
``pydantic_settings.BaseSettings`` covering the full environment surface
(``AIOPS_DATABASE_URL``, ``AIOPS_REDIS_URL``, ``AIOPS_TEMPORAL_TARGET``,
``AIOPS_LANGFUSE_*``, ``AIOPS_FEISHU_*``, ``AIOPS_NETBOX_*``,
``AIOPS_KILL_SWITCH_*`` etc.). See plan Task 2 for the full schema.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Bootstrap settings available before full infrastructure wiring.

    Attributes:
        app_name: Application identifier propagated to every telemetry layer
            (Langfuse trace ``service.name``, Prometheus ``service`` label,
            structlog ``app`` field, Bot self-introduction). Must stay aligned
            with ``pyproject.toml`` ``[project].name`` and ``plugin.yaml``
            ``name`` — mismatches caused the original
            ``aiops-v2 has no plugin.yaml`` Hermes warning that motivated
            architecture §5.5.
    """

    app_name: str = "aiops"
