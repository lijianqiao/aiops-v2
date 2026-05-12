"""Prompt-injection sanitization helpers for untrusted prompt content."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from prometheus_client import Counter

BLOCKED_MARKER = "[blocked: suspicious pattern detected]"
TRUNCATED_SUFFIX = "...[truncated]"
MAX_UNTRUSTED_CHARS = 4000
_BIDI_CONTROL_CHARS = {
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}

PROMPT_INJECTION_BLOCKED_TOTAL = Counter(
    "prompt_injection_blocked_total",
    "Count of untrusted prompt blocks blocked by sanitization pattern.",
    labelnames=("pattern",),
)


@dataclass(frozen=True, slots=True)
class InjectionPattern:
    """Compiled prompt-injection blacklist pattern."""

    identifier: str
    regex: re.Pattern[str]


def _repo_root() -> Path:
    """Return the workspace root for config lookups."""
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_injection_patterns() -> tuple[InjectionPattern, ...]:
    """Load and compile prompt-injection blacklist patterns from YAML."""
    config_path = _repo_root() / "config" / "injection_patterns.yaml"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    compiled_patterns: list[InjectionPattern] = []
    for item in data.get("patterns", []):
        identifier = item["id"]
        compiled_patterns.append(InjectionPattern(identifier=identifier, regex=re.compile(item["regex"])))
    return tuple(compiled_patterns)


def escape_prompt_special_chars(text: str) -> str:
    """Remove prompt-shaping control characters from untrusted text.

    Args:
        text: Untrusted text from external systems.

    Returns:
        Sanitized text with bidi overrides removed and non-printing control
        characters stripped except for newlines and tabs.
    """
    escaped: list[str] = []
    for character in text:
        if character in _BIDI_CONTROL_CHARS:
            continue
        if unicodedata.category(character) in {"Cc", "Cf"} and character not in {"\n", "\t"}:
            continue
        escaped.append(character)
    return "".join(escaped)


def _truncate(text: str) -> str:
    """Truncate text to the configured prompt budget."""
    if len(text) <= MAX_UNTRUSTED_CHARS:
        return text
    return f"{text[:MAX_UNTRUSTED_CHARS]}{TRUNCATED_SUFFIX}"


def sanitize_untrusted(text: str) -> str:
    """Sanitize untrusted content before it is inserted into a prompt.

    Args:
        text: Untrusted input.

    Returns:
        Escaped and truncated text, or a blocked marker if the content matches
        a prompt-injection blacklist pattern.
    """
    cleaned = _truncate(escape_prompt_special_chars(text))
    for pattern in load_injection_patterns():
        if pattern.regex.search(cleaned):
            PROMPT_INJECTION_BLOCKED_TOTAL.labels(pattern=pattern.identifier).inc()
            return BLOCKED_MARKER
    return cleaned


async def sanitize_prompt_messages(user_message: str, messages: Any | None = None) -> Any:
    """Sanitize untrusted prompt blocks before LLM dispatch.

    Two-mode operation chosen explicitly by the caller:

    - ``messages`` provided → the message container is sanitized in place
      via ``iter_untrusted_blocks`` / ``replace_untrusted_block`` and
      returned. The ``user_message`` argument is ignored.
    - ``messages`` is ``None`` → ``user_message`` is treated as untrusted
      text, sanitized, and returned as a string.

    The ``iter_untrusted_blocks`` result is snapshotted via ``list(...)``
    before iteration so implementations backed by mutable dictionaries
    can safely call ``replace_untrusted_block`` during the loop.

    Args:
        user_message: Raw user text. Sanitized only when ``messages`` is None.
        messages: Optional message container exposing ``iter_untrusted_blocks``
            and ``replace_untrusted_block`` methods.

    Returns:
        The sanitized ``messages`` container when provided, otherwise the
        sanitized ``user_message`` string.
    """
    if messages is not None:
        iter_blocks = getattr(messages, "iter_untrusted_blocks", None)
        replace_block = getattr(messages, "replace_untrusted_block", None)
        if callable(iter_blocks) and callable(replace_block):
            for block_name, block_text in list(iter_blocks()):
                replace_block(block_name, sanitize_untrusted(block_text))
        return messages

    return sanitize_untrusted(user_message)
