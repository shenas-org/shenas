"""Goodreads source -- imports reading data from CSV export.

Goodreads shut down its public API in 2020. This source reads from the
CSV export available at https://www.goodreads.com/review/import.
Configure the ``csv_path`` setting to point to the exported file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from shenas_plugins.core.base_config import SourceConfig
from shenas_plugins.core.table import Field
from shenas_sources.core.source import Source


class GoodreadsSource(Source):
    name = "goodreads"
    display_name = "Goodreads"
    primary_table = "readings"
    description = (
        "Imports reading history, ratings, and shelf data from a Goodreads CSV export.\n\n"
        "Goodreads has no public API. Export your library from\n"
        "https://www.goodreads.com/review/import and set the csv_path config."
    )

    @dataclass
    class Config(SourceConfig):
        csv_path: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description="Path to the Goodreads CSV export file",
                    ui_widget="text",
                    example_value="/path/to/goodreads_library_export.csv",
                ),
            ]
            | None
        ) = None

    # No auth needed for CSV import
    auth_instructions = ""

    def build_client(self) -> Any:
        return None

    def sync(self, *, full_refresh: bool = False, **_kwargs: Any) -> None:
        """Custom sync: reads CSV from configured path."""
        from shenas_sources.core.cli import run_sync
        from shenas_sources.goodreads.tables import TABLES

        row = self.Config.read_row()
        csv_path_str = row.get("csv_path") if row else None
        if not csv_path_str:
            msg = "No csv_path configured. Set it in the Config tab."
            raise RuntimeError(msg)

        csv_path = Path(csv_path_str)
        if not csv_path.exists():
            msg = f"CSV file not found: {csv_path}"
            raise RuntimeError(msg)

        resources = [t.to_resource(csv_path) for t in TABLES]
        run_sync("goodreads", "goodreads", resources, full_refresh, self._auto_transform)
        self._mark_synced()

    def resources(self, _client: Any) -> list[Any]:
        return []  # sync() is overridden
