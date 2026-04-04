"""Obsidian pipe -- extracts frontmatter from daily notes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from shenas_pipes.core.pipe import Pipe
from shenas_plugins.core.base_config import PipeConfig
from shenas_schemas.core.field import Field


class ObsidianPipe(Pipe):
    name = "obsidian"
    display_name = "Obsidian"
    primary_table = "daily_notes"
    description = (
        "Extracts frontmatter fields from Obsidian daily notes.\n\n"
        "Scans a configured daily notes folder for markdown files, parses YAML "
        "frontmatter, and loads the key-value pairs into DuckDB. No API auth "
        "needed -- just configure the vault path."
    )

    @dataclass
    class Config(PipeConfig):
        daily_notes_folder: (
            Annotated[
                str,
                Field(
                    db_type="VARCHAR",
                    description="Path to Obsidian daily notes folder",
                    ui_widget="text",
                    example_value="/home/user/vault/daily",
                ),
            ]
            | None
        ) = None

    def build_client(self) -> Any:
        row = self._config_store.get(self.Config)
        folder = row.get("daily_notes_folder") if row else None
        if not folder:
            msg = "Daily notes folder not configured. Set it in the Config tab."
            raise RuntimeError(msg)
        return folder

    def resources(self, client: Any) -> list[Any]:
        from shenas_pipes.obsidian.source import daily_notes

        return [daily_notes(client)]
