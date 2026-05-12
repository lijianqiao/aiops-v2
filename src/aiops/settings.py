"""Typed runtime settings for the AIOps platform.

The settings layer centralizes every infrastructure-facing configuration
surface behind a single ``BaseSettings`` model loaded from environment
variables prefixed with ``AIOPS_``.

Design notes:
    - Sensitive credentials use ``SecretStr`` so they are masked in ``repr``,
      ``ValidationError`` messages, and structured-logging context dumps.
    - Numeric safety caps carry ``Field(gt=0)`` lower bounds so operator
      typos cannot silently disable kill-switches or cost caps.
    - ``hermes_instance`` is a typed ``Literal`` so unknown roles fail at
      Settings construction rather than deep inside Hermes plugin dispatch.
    - Feishu credentials are **intentionally absent**: they are owned by the
      Hermes process (see ``~/.hermes/config.yaml``) and our plugin reaches
      Feishu only through ``ctx.register_command`` / Hermes-mediated APIs.
      Duplicating them here would create a second source of truth and a
      larger credential exposure surface.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

HermesRole = Literal["gateway", "linux", "network", "infra"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name: Logical application name propagated to telemetry. Must match
            ``pyproject.toml`` ``[project].name`` and ``plugin.yaml`` ``name``.
        hermes_instance: Hermes instance role used by ``register(ctx)`` to load
            a role-specific tool subset and preserve credential isolation.
        database_url: Async SQLAlchemy database URL.
        redis_url: Redis connection URL.
        temporal_target: Temporal frontend address.
        temporal_namespace: Temporal namespace name.
        temporal_task_queue: Default Temporal task queue.
        litellm_endpoint: LiteLLM gateway base URL.
        langfuse_host: Langfuse API / UI host.
        langfuse_public_key: Langfuse public API key.
        langfuse_secret_key: Langfuse secret API key (masked).
        netbox_url: NetBox endpoint.
        netbox_token: NetBox API token (masked).
        kill_switch_key_prefix: Redis prefix used for kill switch keys.
        cost_cap_usd_per_incident: Maximum allowed LLM cost per incident (USD).
            Strictly positive — zero would silently disable cost caps.
        activity_cap_per_incident: Maximum Activity executions per incident.
        hermes_tool_cap_per_incident: Maximum Hermes tool calls per incident.
        sync_await_timeout_sec: Mode A sync wait timeout in seconds. Bounded to
            ``(0, 600]`` so misconfiguration cannot pin Hermes sessions
            indefinitely.
    """

    model_config = SettingsConfigDict(env_prefix="AIOPS_", env_file=".env", extra="ignore")

    app_name: str = "aiops"
    hermes_instance: HermesRole = "gateway"

    database_url: str = "postgresql+asyncpg://aiops:aiops@localhost:5432/aiops"
    redis_url: str = "redis://localhost:6379/0"

    temporal_target: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "aiops"

    litellm_endpoint: str = "http://localhost:4000"

    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr = SecretStr("")

    netbox_url: str = "http://localhost:8000"
    netbox_token: SecretStr = SecretStr("")

    kill_switch_key_prefix: str = "aiops:kill_switch"
    cost_cap_usd_per_incident: Annotated[float, Field(gt=0)] = 1.0
    activity_cap_per_incident: Annotated[int, Field(gt=0)] = 50
    hermes_tool_cap_per_incident: Annotated[int, Field(gt=0)] = 30
    sync_await_timeout_sec: Annotated[int, Field(gt=0, le=600)] = 60
