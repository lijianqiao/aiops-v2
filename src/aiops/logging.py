"""Structured logging configuration for the AIOps platform.

Both ``structlog`` and the stdlib ``logging`` framework are wired to emit
single-line JSON to stdout. This keeps logs from third-party libraries
(SQLAlchemy, asyncpg, temporalio, httpx, langfuse) on the same parser path
as our own logs so Promtail / jq pipelines have one schema to handle.

``configure_logging()`` is idempotent — repeated calls (in tests, or because
``build_app()`` runs multiple times) replace handlers cleanly instead of
stacking them.

``structlog.contextvars.merge_contextvars`` is included in the processor
chain so hooks / interceptors can call
``structlog.contextvars.bind_contextvars(trace_id=...)`` and have those
fields appear on every downstream log line automatically.
"""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import Processor


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog + stdlib logging to emit JSON to stdout.

    Args:
        level: Root log level shared by stdlib loggers and structlog.
            Defaults to ``logging.INFO``.
    """
    shared_processors: list[Processor] = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.contextvars.merge_contextvars,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
