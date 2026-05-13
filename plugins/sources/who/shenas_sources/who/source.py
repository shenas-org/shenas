"""WHO source -- Global Health Observatory country-level health indicators.

No authentication required. Configure ISO country codes in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.access_type import PUBLIC_DATASET
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class WHOSource(Source):
    name = "who"
    display_name = "WHO"
    primary_table = "indicators"
    entity_types: ClassVar[list[str]] = ["country"]
    description = (
        "Country-level health indicators from the WHO Global Health Observatory.\n\n"
        "Covers life expectancy, mortality, vaccination coverage, healthcare "
        "spending, disease burden, and 2000+ other indicators for 194 member states.\n\n"
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
        from shenas_sources.who.client import WHOClient

        codes = self._resolve_country_codes(alpha3=True) or None
        return WHOClient(country_codes=codes, log=self.log)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.who.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
