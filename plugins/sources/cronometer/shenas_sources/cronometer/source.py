"""Cronometer source -- imports nutrition data from exported CSV files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class CronometerSource(Source):
    name = "cronometer"
    display_name = "Cronometer"
    primary_table = "daily_nutrition"
    entity_types: ClassVar[list[str]] = ["human"]
    description = (
        "Imports nutrition data from Cronometer CSV exports.\n\n"
        "Export your data from Cronometer (Settings > Export Data) and drop "
        "the CSV files into a configured directory. Supports the "
        '"Daily Nutrition" and "Servings" export formats.'
    )

    @dataclass
    class Config(SourceConfig):
        export_dir: (
            Annotated[
                str,
                Field(
                    db_type="VARCHAR",
                    description="Directory containing Cronometer CSV export files",
                    ui_widget="text",
                    example_value="~/Downloads/cronometer",
                ),
            ]
            | None
        ) = None

    def build_client(self) -> Any:
        row = self.Config.read_row()
        configured = row.get("export_dir") if row else None
        if not configured:
            msg = "Export directory not configured. Set it in the Config tab."
            raise RuntimeError(msg)
        path = str(Path(configured).expanduser())
        if not Path(path).is_dir():
            msg = f"Export directory not found: {path}"
            raise RuntimeError(msg)
        return path

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.cronometer.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
