"""Tests for Claude Code source tables."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from shenas_sources.claude_code.tables import Prompts, Turns

if TYPE_CHECKING:
    from pathlib import Path


def test_prompts_extract(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    history.write_text(
        "\n".join(
            json.dumps(entry)
            for entry in [
                {
                    "display": "explain this function",
                    "pastedContents": {},
                    "timestamp": 1704067200000,
                    "project": "/home/user/myproject",
                    "sessionId": "abc-123",
                },
                {
                    "display": "fix the bug in main.py",
                    "pastedContents": {},
                    "timestamp": 1704067260000,
                    "project": "/home/user/myproject",
                    "sessionId": "abc-123",
                },
            ]
        )
        + "\n"
    )
    rows = list(Prompts.extract(str(tmp_path)))
    assert len(rows) == 2

    assert rows[0]["prompt"] == "explain this function"
    assert rows[0]["project"] == "/home/user/myproject"
    assert rows[0]["session_id"] == "abc-123"
    assert rows[0]["prompted_at"] is not None

    assert rows[1]["prompt"] == "fix the bug in main.py"


def test_prompts_skips_empty(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    history.write_text(json.dumps({"display": "", "timestamp": 1704067200000, "sessionId": "x"}) + "\n")
    rows = list(Prompts.extract(str(tmp_path)))
    assert len(rows) == 0


def test_prompts_missing_file(tmp_path: Path) -> None:
    rows = list(Prompts.extract(str(tmp_path)))
    assert len(rows) == 0


def test_turns_extract(tmp_path: Path) -> None:
    projects = tmp_path / "projects" / "-home-user-myproject"
    projects.mkdir(parents=True)
    conv = projects / "session-abc.jsonl"
    conv.write_text(
        "\n".join(
            json.dumps(entry)
            for entry in [
                {"type": "permission-mode", "permissionMode": "default", "sessionId": "abc"},
                {
                    "type": "system",
                    "subtype": "turn_duration",
                    "durationMs": 15000,
                    "messageCount": 12,
                    "timestamp": "2024-01-01T12:00:00.000Z",
                    "sessionId": "abc-123",
                    "cwd": "/home/user/myproject",
                    "entrypoint": "cli",
                },
                {
                    "type": "system",
                    "subtype": "turn_duration",
                    "durationMs": 45000,
                    "messageCount": 30,
                    "timestamp": "2024-01-01T12:05:00.000Z",
                    "sessionId": "abc-123",
                    "cwd": "/home/user/myproject",
                    "entrypoint": "cli",
                },
            ]
        )
        + "\n"
    )
    rows = list(Turns.extract(str(tmp_path)))
    assert len(rows) == 2

    assert rows[0]["duration_ms"] == 15000
    assert rows[0]["message_count"] == 12
    assert rows[0]["session_id"] == "abc-123"
    assert rows[0]["project"] == "/home/user/myproject"
    assert rows[0]["entrypoint"] == "cli"
    assert rows[0]["completed_at"] is not None

    assert rows[1]["duration_ms"] == 45000
    assert rows[1]["message_count"] == 30


def test_turns_skips_non_duration(tmp_path: Path) -> None:
    projects = tmp_path / "projects" / "test"
    projects.mkdir(parents=True)
    conv = projects / "session.jsonl"
    conv.write_text(json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n")
    rows = list(Turns.extract(str(tmp_path)))
    assert len(rows) == 0


def test_turns_missing_dir(tmp_path: Path) -> None:
    rows = list(Turns.extract(str(tmp_path)))
    assert len(rows) == 0


def test_stable_ids(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    history.write_text(
        json.dumps(
            {
                "display": "hello",
                "timestamp": 1704067200000,
                "project": "/p",
                "sessionId": "s",
            }
        )
        + "\n"
    )
    rows1 = list(Prompts.extract(str(tmp_path)))
    rows2 = list(Prompts.extract(str(tmp_path)))
    assert rows1[0]["id"] == rows2[0]["id"]
