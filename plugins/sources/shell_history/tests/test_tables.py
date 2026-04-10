"""Tests for shell history source tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shenas_sources.shell_history.tables import Commands

if TYPE_CHECKING:
    from pathlib import Path


def test_zsh_extract(tmp_path: Path) -> None:
    hist = tmp_path / ".zsh_history"
    hist.write_text(": 1704067200:0;ls -la\n: 1704067205:2;cd /home\n")
    rows = list(Commands.extract(str(hist)))
    assert len(rows) == 2

    assert rows[0]["command"] == "ls -la"
    assert rows[0]["shell"] == "zsh"
    assert rows[0]["executed_at"] is not None
    assert rows[0]["duration_s"] is None  # 0 -> None

    assert rows[1]["command"] == "cd /home"
    assert rows[1]["duration_s"] == 2.0


def test_bash_with_timestamps(tmp_path: Path) -> None:
    hist = tmp_path / ".bash_history"
    hist.write_text("#1704067200\nls -la\n#1704067205\ncd /home\n")
    rows = list(Commands.extract(str(hist)))
    assert len(rows) == 2

    assert rows[0]["command"] == "ls -la"
    assert rows[0]["shell"] == "bash"
    assert rows[0]["executed_at"] is not None

    assert rows[1]["command"] == "cd /home"


def test_bash_without_timestamps(tmp_path: Path) -> None:
    hist = tmp_path / ".bash_history"
    hist.write_text("ls -la\ncd /home\n")
    rows = list(Commands.extract(str(hist)))
    assert len(rows) == 2
    assert rows[0]["executed_at"] is None
    assert rows[0]["shell"] == "bash"


def test_fish_extract(tmp_path: Path) -> None:
    hist = tmp_path / "fish_history"
    hist.write_text("- cmd: ls -la\n  when: 1704067200\n- cmd: cd /home\n  when: 1704067205\n")
    rows = list(Commands.extract(str(hist)))
    assert len(rows) == 2

    assert rows[0]["command"] == "ls -la"
    assert rows[0]["shell"] == "fish"
    assert rows[0]["executed_at"] is not None


def test_stable_ids(tmp_path: Path) -> None:
    hist = tmp_path / ".zsh_history"
    hist.write_text(": 1704067200:0;ls -la\n")
    rows1 = list(Commands.extract(str(hist)))
    rows2 = list(Commands.extract(str(hist)))
    assert rows1[0]["id"] == rows2[0]["id"]
