"""Goodreads source -- scrapes public shelf data via RSS feeds.

Goodreads shut down its public API in 2020 but still exposes public
shelf data via RSS at ``goodreads.com/review/list_rss/<user_id>``.
This source fetches all items from the user's read, currently-reading,
and to-read shelves and extracts book metadata, ratings, and dates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class GoodreadsSource(Source):
    name = "goodreads"
    display_name = "Goodreads"
    primary_table = "readings"
    entity_types: ClassVar[list[str]] = ["human"]
    description = (
        "Scrapes public reading history, ratings, and shelf data from Goodreads.\n\n"
        "Uses RSS feeds -- no API key needed. Set your Goodreads user ID in config.\n"
        "Find it in your profile URL: goodreads.com/user/show/<user_id>"
    )

    @dataclass
    class Config(SourceConfig):
        user_id: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description="Goodreads user ID (from your profile URL: goodreads.com/user/show/<id>)",
                    ui_widget="text",
                    example_value="12345678",
                ),
            ]
            | None
        ) = None

    # No auth needed -- RSS feeds are public
    auth_instructions = ""

    def build_client(self) -> Any:
        from shenas_sources.goodreads.client import GoodreadsClient

        row = self.Config.read_row()
        user_id = row.get("user_id") if row else None
        if not user_id:
            msg = "No user_id configured. Set it in the Config tab."
            raise RuntimeError(msg)
        return GoodreadsClient(user_id)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.goodreads.tables import TABLES

        entries = client.get_all_shelves()
        return [t.to_resource(client, entries=entries) for t in TABLES]
