"""IMF source -- World Economic Outlook country-level macroeconomic data.

No authentication required. Uses the DataMapper API for WEO indicators.
Configure ISO country codes in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class IMFSource(Source):
    name = "imf"
    display_name = "IMF"
    primary_table = "weo_indicators"
    description = (
        "Country-level macroeconomic data from the IMF World Economic Outlook.\n\n"
        "Covers GDP growth, inflation, unemployment, government debt, current "
        "account balance, and other key economic indicators for 190+ countries.\n\n"
        "No API key required. Set ISO country codes in the Config tab."
    )

    @dataclass
    class Config(SourceConfig):
        country_codes: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description="Comma-separated IMF country codes (e.g. USA,DEU,SWE) or leave blank for all",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.imf.client import IMFClient

        cfg = self.Config.read_row()
        codes = None
        if cfg and cfg.get("country_codes"):
            codes = [c.strip() for c in cfg["country_codes"].split(",") if c.strip()]
        return IMFClient(country_codes=codes)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.imf.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
