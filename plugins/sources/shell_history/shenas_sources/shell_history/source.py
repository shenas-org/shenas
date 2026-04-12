"""Shell history source -- extracts command history from bash, zsh, or fish."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from shenas_plugins.core.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


def _default_history_file() -> str:
    """Guess the default history file for the current user's shell."""
    home = Path.home()
    # Try zsh first (most common with extended history), then bash, then fish.
    zsh = home / ".zsh_history"
    if zsh.exists():
        return str(zsh)
    bash = home / ".bash_history"
    if bash.exists():
        return str(bash)
    fish = home / ".local" / "share" / "fish" / "fish_history"
    if fish.exists():
        return str(fish)
    return ""


class ShellHistorySource(Source):
    name = "shell_history"
    display_name = "Shell History"
    primary_table = "commands"
    description = (
        "Extracts command history from bash, zsh, or fish shell history files.\n\n"
        "Parses timestamps (where available) and commands. Zsh extended history "
        "also provides command duration. No API auth needed -- just configure "
        "the history file path."
    )

    @dataclass
    class Config(SourceConfig):
        history_file: (
            Annotated[
                str,
                Field(
                    db_type="VARCHAR",
                    description="Path to shell history file",
                    ui_widget="text",
                    example_value="~/.zsh_history",
                ),
            ]
            | None
        ) = None

    def build_client(self) -> Any:
        row = self.Config.read_row()
        configured = row.get("history_file") if row else None
        path = str(Path(configured).expanduser()) if configured else _default_history_file()
        if not path or not Path(path).exists():
            msg = "Shell history file not found. Set the path in the Config tab."
            raise RuntimeError(msg)
        return path

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.shell_history.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
