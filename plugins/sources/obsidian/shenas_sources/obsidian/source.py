"""Obsidian pipe -- extracts frontmatter from daily notes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from shenas_plugins.core.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class ObsidianSource(Source):
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
    class Config(SourceConfig):
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
        habits_heading: Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Heading whose top-level checkboxes are extracted into the habits table",
                default="Plan for the day",
                ui_widget="text",
                example_value="Plan for the day",
            ),
        ] = "Plan for the day"

    def build_client(self) -> Any:
        row = self.Config.read_row()
        folder = row.get("daily_notes_folder") if row else None
        if not folder:
            msg = "Daily notes folder not configured. Set it in the Config tab."
            raise RuntimeError(msg)
        return folder

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.obsidian.tables import TABLES

        row = self.Config.read_row()
        heading = (row.get("habits_heading") if row else None) or "Plan for the day"

        return [t.to_resource(client, heading=heading) for t in TABLES]
