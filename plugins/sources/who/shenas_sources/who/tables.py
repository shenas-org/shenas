"""WHO source tables.

- ``Indicators`` -- annual health indicator values per country. One row per
  (country, indicator, year). Covers 22 core health indicators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import AggregateTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.who.client import WHOClient


class Indicators(AggregateTable):
    """Annual health indicator values per country from WHO GHO."""

    class _Meta:
        name = "indicators"
        display_name = "Indicators"
        description = (
            "Annual values for 22 core health indicators per country (life expectancy, mortality, vaccination, etc.)."
        )
        pk = ("country_code", "indicator_code", "year")

    time_at: ClassVar[str] = "year"

    country_code: Annotated[
        str, Field(db_type="VARCHAR", description="ISO 3166-1 alpha-3 country code", display_name="Country Code")
    ] = ""
    indicator_code: Annotated[
        str, Field(db_type="VARCHAR", description="WHO GHO indicator code", display_name="Indicator Code")
    ] = ""
    indicator_name: Annotated[str, Field(db_type="VARCHAR", description="Indicator description", display_name="Indicator")] = (
        ""
    )
    year: Annotated[int, Field(db_type="INTEGER", description="Calendar year", display_name="Year")] = 0
    value: Annotated[float | None, Field(db_type="DOUBLE", description="Indicator value", display_name="Value")] = None
    value_low: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Lower confidence bound", display_name="Low"),
    ] = None
    value_high: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Upper confidence bound", display_name="High"),
    ] = None

    @classmethod
    def extract(cls, client: WHOClient, **_: Any) -> Iterator[dict[str, Any]]:
        from shenas_sources.who.client import CORE_INDICATORS

        for indicator_code in CORE_INDICATORS:
            yield from client.get_indicator(indicator_code)


TABLES = (Indicators,)
