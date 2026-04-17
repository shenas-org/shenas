"""Shell history source tables.

Parses bash, zsh (extended history), and fish history files into a single
``Commands`` EventTable. The shell type is auto-detected from file content.

Zsh extended history format: ``: <epoch>:<duration>;<command>``
Bash with HISTTIMEFORMAT:    ``#<epoch>`` on the line before the command
Fish history (YAML-like):    ``- cmd: <command>`` / ``  when: <epoch>``
"""

from __future__ import annotations

import contextlib
import hashlib
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

from app.relation import PlotHint
from app.table import Field
from shenas_sources.core.table import EventTable, SourceTable

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

_ZSH_RE = re.compile(r"^: (\d+):(\d+);(.+)$", re.DOTALL)
_BASH_TS_RE = re.compile(r"^#(\d+)$")


def _parse_zsh(text: str) -> Iterator[dict[str, Any]]:
    """Parse zsh extended history (EXTENDED_HISTORY option)."""
    for line in text.splitlines():
        m = _ZSH_RE.match(line)
        if not m:
            continue
        epoch, duration, cmd = int(m.group(1)), int(m.group(2)), m.group(3).strip()
        if not cmd:
            continue
        yield {
            "executed_at": datetime.fromtimestamp(epoch, tz=UTC).isoformat(),
            "command": cmd,
            "duration_s": float(duration) if duration else None,
            "shell": "zsh",
        }


def _parse_bash(text: str) -> Iterator[dict[str, Any]]:
    """Parse bash history, with optional ``#timestamp`` lines."""
    lines = text.splitlines()
    pending_ts: int | None = None
    for line in lines:
        ts_match = _BASH_TS_RE.match(line)
        if ts_match:
            pending_ts = int(ts_match.group(1))
            continue
        cmd = line.strip()
        if not cmd:
            continue
        executed_at = datetime.fromtimestamp(pending_ts, tz=UTC).isoformat() if pending_ts else None
        pending_ts = None
        yield {
            "executed_at": executed_at,
            "command": cmd,
            "duration_s": None,
            "shell": "bash",
        }


def _parse_fish(text: str) -> Iterator[dict[str, Any]]:
    """Parse fish history (YAML-like: ``- cmd: ...`` / ``  when: ...``)."""
    cmd: str | None = None
    when: int | None = None
    for line in text.splitlines():
        if line.startswith("- cmd: "):
            if cmd is not None:
                yield _fish_row(cmd, when)
            cmd = line[7:].strip()
            when = None
        elif line.startswith("  when: ") and cmd is not None:
            with contextlib.suppress(ValueError):
                when = int(line[8:].strip())
    if cmd is not None:
        yield _fish_row(cmd, when)


def _fish_row(cmd: str, when: int | None) -> dict[str, Any]:
    return {
        "executed_at": datetime.fromtimestamp(when, tz=UTC).isoformat() if when else None,
        "command": cmd,
        "duration_s": None,
        "shell": "fish",
    }


def _detect_and_parse(text: str) -> Iterator[dict[str, Any]]:
    """Auto-detect shell type from file content and parse."""
    if text.startswith(": ") or "\n: " in text[:500]:
        yield from _parse_zsh(text)
    elif text.startswith("- cmd:") or "\n- cmd:" in text[:500]:
        yield from _parse_fish(text)
    else:
        yield from _parse_bash(text)


def _make_id(executed_at: str | None, command: str) -> str:
    """Stable content-based ID from timestamp + command."""
    raw = f"{executed_at or ''}:{command}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


class Commands(EventTable):
    """Shell command from history file."""

    class _Meta:
        name = "commands"
        display_name = "Commands"
        description = "Shell commands from bash, zsh, or fish history."
        pk = ("id",)
        time_at = "executed_at"
        plot = (PlotHint("duration_s"),)

    id: Annotated[str, Field(db_type="VARCHAR", description="Content-hash ID (sha256[:16])", display_name="ID")] = ""
    command: Annotated[str, Field(db_type="VARCHAR", description="The shell command", display_name="Command")] = ""
    executed_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Command execution timestamp (UTC)", display_name="Executed At"),
    ] = None
    duration_s: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Command duration (zsh extended history only)", display_name="Duration", unit="s"),
    ] = None
    shell: Annotated[
        str | None, Field(db_type="VARCHAR", description="Shell type (bash, zsh, fish)", display_name="Shell")
    ] = None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        text = _read_history(client)
        for row in _detect_and_parse(text):
            row["id"] = _make_id(row.get("executed_at"), row["command"])
            yield row


def _read_history(path: str) -> str:
    """Read history file, tolerating encoding errors."""
    from pathlib import Path

    return Path(path).read_text(encoding="utf-8", errors="replace")


TABLES: tuple[type[SourceTable], ...] = (Commands,)
