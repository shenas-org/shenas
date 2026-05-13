"""IMF source -- World Economic Outlook country-level macroeconomic data.

No authentication required. Uses the DataMapper API for WEO indicators.
Configure ISO country codes in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.access_type import PUBLIC_DATASET
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class IMFSource(Source):
    name = "imf"
    display_name = "IMF"
    primary_table = "weo_indicators"
    entity_types: ClassVar[list[str]] = ["country"]
    description = (
        "Country-level macroeconomic data from the IMF World Economic Outlook.\n\n"
        "Covers GDP growth, inflation, unemployment, government debt, current "
        "account balance, and other key economic indicators for 190+ countries.\n\n"
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
                description="Select countries to fetch data for (leave empty for all)",
                ui_widget="entity_picker",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.imf.client import IMFClient

        codes = self._resolve_country_codes(alpha3=True) or None
        return IMFClient(country_codes=codes)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.imf.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
