"""World Bank source -- country-level development indicators.

No authentication required. Configure ISO country codes in the Config tab.
Over 1400 indicators available back to 1960.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class WorldBankSource(Source):
    name = "worldbank"
    display_name = "World Bank"
    primary_table = "indicators"
    description = (
        "Country-level development indicators from the World Bank Open Data API.\n\n"
        "Covers GDP, population, inflation, trade, education, health, and 1400+ "
        "other indicators for 200+ countries. Annual data back to 1960.\n\n"
        "No API key required. Set ISO country codes in the Config tab."
    )

    @dataclass
    class Config(SourceConfig):
        country_codes: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description="Comma-separated ISO 3166-1 alpha-2 country codes (e.g. SE,DE,US) or 'all' for all countries",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.worldbank.client import WorldBankClient

        cfg = self.Config.read_row()
        if not cfg or not cfg.get("country_codes"):
            msg = "Set country codes in the Config tab (e.g. SE,DE,US or 'all')."
            raise RuntimeError(msg)
        codes = cfg["country_codes"].strip()
        return WorldBankClient(country_codes=codes)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.worldbank.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
