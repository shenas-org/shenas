"""OECD source -- country-level economic and social statistics.

No authentication required. Uses the SDMX REST API at sdmx.oecd.org.
Configure ISO country codes in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class OECDSource(Source):
    name = "oecd"
    display_name = "OECD"
    primary_table = "indicators"
    description = (
        "Country-level economic and social statistics from the OECD.\n\n"
        "Covers GDP, unemployment, CPI, tax revenue, education spending, "
        "R&D expenditure, broadband penetration, and trade data for 38 OECD "
        "member countries.\n\n"
        "No API key required. Set ISO country codes in the Config tab."
    )

    @dataclass
    class Config(SourceConfig):
        country_codes: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description=(
                    "Comma-separated ISO 3166-1 alpha-3 country codes (e.g. USA,DEU,SWE) or leave blank for all OECD members"
                ),
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.oecd.client import OECDClient

        cfg = self.Config.read_row()
        codes = None
        if cfg and cfg.get("country_codes"):
            codes = [c.strip() for c in cfg["country_codes"].split(",") if c.strip()]
        return OECDClient(country_codes=codes)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.oecd.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
