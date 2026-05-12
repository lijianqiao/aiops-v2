"""Bot-facing card and command result contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BotCard(BaseModel):
    """Normalized Bot card content emitted by command handlers.

    Attributes:
        title: Primary card title.
        body: Main textual content.
        metadata: Supplemental metadata for routing or callbacks.
    """

    title: str
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BotCommandResult(BaseModel):
    """Structured result returned by Bot command handlers.

    Attributes:
        ok: Whether the command succeeded.
        message: Human-readable command summary.
        cards: Optional cards emitted by the command.
        data: Optional structured payload for downstream handlers.
    """

    ok: bool
    message: str
    cards: list[BotCard] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
