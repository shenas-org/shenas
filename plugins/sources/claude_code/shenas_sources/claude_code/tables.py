"""Claude Code source tables.

Extracts two tables from local Claude Code data:

- **Prompts**: user inputs from ``~/.claude/history.jsonl``
- **Turns**: assistant turn statistics from conversation JSONL files
  in ``~/.claude/projects/*/*.jsonl`` (``system``/``turn_duration`` entries)
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import EventTable

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger("shenas.sources.claude_code")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts_to_iso(epoch_ms: float | None) -> str | None:
    """Convert epoch milliseconds to ISO 8601 UTC string."""
    if epoch_ms is None:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC).isoformat()


def _make_id(*parts: str | None) -> str:
    """Stable content-based ID from concatenated parts."""
    raw = ":".join(p or "" for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Prompts table
# ---------------------------------------------------------------------------


class Prompts(EventTable):
    """User prompt submitted to Claude Code."""

    class _Meta:
        name = "prompts"
        display_name = "Prompts"
        description = "User prompts submitted to Claude Code."
        pk = ("id",)

    time_at: ClassVar[str] = "prompted_at"

    id: Annotated[str, Field(db_type="VARCHAR", description="Content-hash ID (sha256[:16])")] = ""
    prompt: Annotated[str, Field(db_type="VARCHAR", description="The user prompt text")] = ""
    project: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Project working directory"),
    ] = None
    session_id: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Claude Code session ID"),
    ] = None
    prompted_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Prompt submission timestamp (UTC)"),
    ] = None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        history_file = Path(client) / "history.jsonl"
        if not history_file.exists():
            logger.warning("history.jsonl not found in %s", client)
            return

        for line in history_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            prompt_text = entry.get("display", "").strip()
            if not prompt_text:
                continue

            ts = _ts_to_iso(entry.get("timestamp"))
            yield {
                "id": _make_id(str(entry.get("timestamp", "")), prompt_text),
                "prompt": prompt_text,
                "project": entry.get("project"),
                "session_id": entry.get("sessionId"),
                "prompted_at": ts,
            }


# ---------------------------------------------------------------------------
# Turns table
# ---------------------------------------------------------------------------


class Turns(EventTable):
    """Assistant turn statistics from Claude Code conversations."""

    class _Meta:
        name = "turns"
        display_name = "Turns"
        description = "Assistant turn durations and message counts from Claude Code sessions."
        pk = ("id",)

    time_at: ClassVar[str] = "completed_at"

    id: Annotated[str, Field(db_type="VARCHAR", description="Content-hash ID (sha256[:16])")] = ""
    session_id: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Claude Code session ID"),
    ] = None
    duration_ms: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Turn duration in milliseconds", unit="ms"),
    ] = None
    message_count: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Number of messages in the turn"),
    ] = None
    project: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Project working directory"),
    ] = None
    entrypoint: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="How Claude Code was launched (cli, ide, etc.)"),
    ] = None
    completed_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Turn completion timestamp (UTC)"),
    ] = None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        projects_dir = Path(client) / "projects"
        if not projects_dir.exists():
            logger.warning("projects/ directory not found in %s", client)
            return

        for jsonl_file in projects_dir.rglob("*.jsonl"):
            yield from _parse_conversation_turns(jsonl_file)


def _parse_conversation_turns(path: Path) -> Iterator[dict[str, Any]]:
    """Extract turn_duration entries from a conversation JSONL file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.warning("Could not read %s", path)
        return

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") != "system" or entry.get("subtype") != "turn_duration":
            continue

        ts = entry.get("timestamp")
        session_id = entry.get("sessionId")
        duration_ms = entry.get("durationMs")
        message_count = entry.get("messageCount")

        yield {
            "id": _make_id(session_id, ts, str(duration_ms)),
            "session_id": session_id,
            "duration_ms": duration_ms,
            "message_count": message_count,
            "project": entry.get("cwd"),
            "entrypoint": entry.get("entrypoint"),
            "completed_at": ts,
        }


TABLES: tuple[type, ...] = (Prompts, Turns)
