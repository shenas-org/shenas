"""Freedom House source -- Freedom in the World country scores.

No authentication required. Downloads the aggregate Excel dataset from
freedomhouse.org and parses it into structured rows.
"""

from __future__ import annotations

from typing import Any

from shenas_sources.core.source import Source


class FreedomHouseSource(Source):
    name = "freedomhouse"
    display_name = "Freedom House"
    primary_table = "freedom_scores"
    description = (
        "Freedom in the World scores from Freedom House.\n\n"
        "Annual political rights and civil liberties ratings for ~195 countries "
        "and ~15 territories. Data available from 2013 with full sub-indicator "
        "breakdown (25 questions across 7 subcategories).\n\n"
        "No API key required. Downloads the aggregate Excel dataset directly."
    )

    def build_client(self) -> Any:
        from shenas_sources.freedomhouse.client import FreedomHouseClient

        return FreedomHouseClient()

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.freedomhouse.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
