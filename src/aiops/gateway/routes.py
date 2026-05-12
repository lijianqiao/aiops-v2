"""Typed loader for Hermes webhook route configuration."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class RouteDefinition(BaseModel):
    """Single webhook route definition."""

    path: str
    target_instance: str | None = None
    skills: list[str] = Field(default_factory=list)
    prompt: str
    deliver_only: bool = False
    target: str | None = None


class WebhookPlatformConfig(BaseModel):
    """Webhook platform settings exposed to Hermes."""

    enabled: bool
    secret: str
    extra: dict[str, dict[str, RouteDefinition]]


class HermesRoutesConfig(BaseModel):
    """Root configuration model for Hermes route declarations."""

    platforms: dict[str, WebhookPlatformConfig]


def load_routes(config_path: str | Path) -> HermesRoutesConfig:
    """Load and validate the Hermes route configuration file."""
    data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    return HermesRoutesConfig.model_validate(data)
