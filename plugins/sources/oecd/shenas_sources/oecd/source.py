"""OECD source -- country-level economic and social statistics.

No authentication required. Uses the SDMX REST API at sdmx.oecd.org.
Configure ISO country codes in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.access_type import PUBLIC_DATASET
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class OECDSource(Source):
    name = "oecd"
    display_name = "OECD"
    primary_table = "indicators"
    entity_types: ClassVar[list[str]] = ["country"]
    description = (
        "Country-level economic and social statistics from the OECD.\n\n"
        "Covers GDP, unemployment, CPI, tax revenue, education spending, "
        "R&D expenditure, broadband penetration, and trade data for 38 OECD "
        "member countries.\n\n"
        "No API key required. Select countries in the Config tab."
    )
    access_types = (PUBLIC_DATASET,)

    @dataclass
    class Config(SourceConfig):
        country_uuids: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                display_name="Countries",
                description="Select countries to fetch data for (leave empty for all OECD members)",
                ui_widget="entity_picker",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.oecd.client import OECDClient

        codes = self._resolve_country_codes(alpha3=True) or None
        return OECDClient(country_codes=codes)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.oecd.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
