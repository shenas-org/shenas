"""Claude Code source -- extracts prompt history and turn stats from local Claude Code data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


def _default_claude_dir() -> str:
    """Return the default ~/.claude directory."""
    return str(Path.home() / ".claude")


class ClaudeCodeSource(Source):
    name = "claude_code"
    display_name = "Claude Code"
    primary_table = "prompts"
    entity_types: ClassVar[list[str]] = ["device"]
    description = (
        "Extracts usage history from local Claude Code data files.\n\n"
        "Parses prompt history (what you asked) and turn statistics "
        "(response times, message counts) from ~/.claude. "
        "No API auth needed -- just configure the Claude data directory path."
    )

    @dataclass
    class Config(SourceConfig):
        claude_dir: (
            Annotated[
                str,
                Field(
                    db_type="VARCHAR",
                    description="Path to Claude Code data directory",
                    ui_widget="text",
                    example_value="~/.claude",
                ),
            ]
            | None
        ) = None

    def build_client(self) -> Any:
        row = self.Config.read_row()
        configured = row.get("claude_dir") if row else None
        path = str(Path(configured).expanduser()) if configured else _default_claude_dir()
        if not path or not Path(path).exists():
            msg = "Claude Code data directory not found. Set the path in the Config tab."
            raise RuntimeError(msg)
        return path

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.claude_code.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
