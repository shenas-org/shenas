"""World Bank source tables.

- ``Indicators`` -- annual indicator values per country. One row per
  (country, indicator, year). Covers 30 core development indicators.
- ``Countries`` -- country metadata (SCD2-tracked).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from app.table import Field
from shenas_sources.core.table import AggregateTable, DimensionTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.worldbank.client import WorldBankClient


class Indicators(AggregateTable):
    """Annual development indicator values per country."""

    class _Meta:
        name = "indicators"
        display_name = "Indicators"
        description = "Annual values for 30 core development indicators per country (GDP, population, inflation, etc.)."
        pk = ("country_code", "indicator_code", "year")
        time_at = "year"

    country_code: Annotated[
        str, Field(db_type="VARCHAR", description="ISO 3166-1 alpha-3 country code", display_name="Country Code")
    ] = ""
    country_name: Annotated[str, Field(db_type="VARCHAR", description="Country name", display_name="Country")] = ""
    indicator_code: Annotated[
        str, Field(db_type="VARCHAR", description="World Bank indicator code", display_name="Indicator Code")
    ] = ""
    indicator_name: Annotated[str, Field(db_type="VARCHAR", description="Indicator description", display_name="Indicator")] = (
        ""
    )
    year: Annotated[int, Field(db_type="INTEGER", description="Calendar year", display_name="Year")] = 0
    value: Annotated[float | None, Field(db_type="DOUBLE", description="Indicator value", display_name="Value")] = None

    @classmethod
    def extract(cls, client: WorldBankClient, **_: Any) -> Iterator[dict[str, Any]]:
        from shenas_sources.worldbank.client import CORE_INDICATORS

        for indicator_code in CORE_INDICATORS:
            yield from client.get_indicator(indicator_code)


class Countries(DimensionTable):
    """World Bank country metadata."""

    class _Meta:
        name = "countries"
        display_name = "Countries"
        description = "Country metadata: region, income level, capital city, coordinates."
        pk = ("country_code",)

    country_code: Annotated[
        str, Field(db_type="VARCHAR", description="ISO 3166-1 alpha-2 country code", display_name="Code")
    ] = ""
    country_code_iso3: Annotated[
        str, Field(db_type="VARCHAR", description="ISO 3166-1 alpha-3 country code", display_name="ISO3")
    ] = ""
    name: Annotated[str, Field(db_type="VARCHAR", description="Country name", display_name="Name")] = ""
    region: Annotated[str, Field(db_type="VARCHAR", description="World Bank region", display_name="Region")] = ""
    income_level: Annotated[
        str, Field(db_type="VARCHAR", description="Income level classification", display_name="Income Level")
    ] = ""
    lending_type: Annotated[
        str, Field(db_type="VARCHAR", description="World Bank lending type", display_name="Lending Type")
    ] = ""
    capital_city: Annotated[str, Field(db_type="VARCHAR", description="Capital city", display_name="Capital")] = ""
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Capital latitude", display_name="Latitude")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Capital longitude", display_name="Longitude")] = (
        None
    )

    @classmethod
    def extract(cls, client: WorldBankClient, **_: Any) -> Iterator[dict[str, Any]]:
        yield from client.get_countries()


TABLES = (Indicators, Countries)
