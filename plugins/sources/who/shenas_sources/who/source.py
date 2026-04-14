"""WHO source -- Global Health Observatory country-level health indicators.

No authentication required. Configure ISO country codes in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class WHOSource(Source):
    name = "who"
    display_name = "WHO"
    primary_table = "indicators"
    description = (
        "Country-level health indicators from the WHO Global Health Observatory.\n\n"
        "Covers life expectancy, mortality, vaccination coverage, healthcare "
        "spending, disease burden, and 2000+ other indicators for 194 member states.\n\n"
        "No API key required. Set ISO 3166-1 alpha-3 country codes in the Config tab."
    )

    @dataclass
    class Config(SourceConfig):
        country_codes: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description="Comma-separated ISO 3166-1 alpha-3 country codes (e.g. SWE,DEU,USA) or leave blank for all",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.who.client import WHOClient

        cfg = self.Config.read_row()
        codes = None
        if cfg and cfg.get("country_codes"):
            codes = [c.strip() for c in cfg["country_codes"].split(",") if c.strip()]
        return WHOClient(country_codes=codes)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.who.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
