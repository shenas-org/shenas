"""IMF source tables.

- ``WEOIndicators`` -- annual WEO indicator values per country. One row per
  (country, indicator, year). Covers 11 core macroeconomic indicators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import AggregateTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.imf.client import IMFClient


class WEOIndicators(AggregateTable):
    """Annual WEO macroeconomic indicator values per country."""

    class _Meta:
        name = "weo_indicators"
        display_name = "WEO Indicators"
        description = (
            "Annual values for 11 core World Economic Outlook indicators per country "
            "(GDP growth, inflation, unemployment, government debt, etc.)."
        )
        pk = ("country_code", "indicator_code", "year")

    time_at: ClassVar[str] = "year"

    country_code: Annotated[
        str, Field(db_type="VARCHAR", description="IMF country code (3-letter)", display_name="Country Code")
    ] = ""
    indicator_code: Annotated[
        str, Field(db_type="VARCHAR", description="IMF WEO indicator code", display_name="Indicator Code")
    ] = ""
    indicator_name: Annotated[str, Field(db_type="VARCHAR", description="Indicator description", display_name="Indicator")] = (
        ""
    )
    year: Annotated[int, Field(db_type="INTEGER", description="Calendar year", display_name="Year")] = 0
    value: Annotated[float | None, Field(db_type="DOUBLE", description="Indicator value", display_name="Value")] = None

    @classmethod
    def extract(cls, client: IMFClient, **_: Any) -> Iterator[dict[str, Any]]:
        from shenas_sources.imf.client import WEO_INDICATORS

        for indicator_code in WEO_INDICATORS:
            yield from client.get_indicator(indicator_code)


TABLES = (WEOIndicators,)
