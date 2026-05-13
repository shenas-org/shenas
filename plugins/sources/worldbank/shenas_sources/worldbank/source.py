"""World Bank source -- country-level development indicators.

No authentication required. Configure ISO country codes in the Config tab.
Over 1400 indicators available back to 1960.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.access_type import PUBLIC_DATASET
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class WorldBankSource(Source):
    name = "worldbank"
    display_name = "World Bank"
    primary_table = "indicators"
    entity_types: ClassVar[list[str]] = ["country"]
    description = (
        "Country-level development indicators from the World Bank Open Data API.\n\n"
        "Covers GDP, population, inflation, trade, education, health, and 1400+ "
        "other indicators for 200+ countries. Annual data back to 1960.\n\n"
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
                description="Select countries to fetch data for",
                ui_widget="entity_picker",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.worldbank.client import WorldBankClient

        codes = self._resolve_country_codes()
        if not codes:
            msg = "Select countries in the Config tab."
            raise RuntimeError(msg)
        return WorldBankClient(country_codes=",".join(codes))

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.worldbank.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
