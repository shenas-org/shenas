"""OECD source tables.

- ``Indicators`` -- periodic indicator values per country. One row per
  (country, indicator, period). Covers GDP, unemployment, and CPI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from app.table import Field
from shenas_sources.core.table import AggregateTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.oecd.client import OECDClient


class Indicators(AggregateTable):
    """Periodic economic indicator values per country from OECD."""

    class _Meta:
        name = "indicators"
        display_name = "Indicators"
        description = "GDP, unemployment, and CPI data per country from the OECD SDMX API."
        pk = ("country_code", "indicator_name", "period")
        time_at = "period"

    country_code: Annotated[
        str, Field(db_type="VARCHAR", description="ISO 3166-1 alpha-3 country code", display_name="Country Code")
    ] = ""
    indicator_name: Annotated[str, Field(db_type="VARCHAR", description="Indicator description", display_name="Indicator")] = (
        ""
    )
    period: Annotated[
        str,
        Field(db_type="VARCHAR", description="Time period (YYYY for annual, YYYY-Qn for quarterly)", display_name="Period"),
    ] = ""
    value: Annotated[float | None, Field(db_type="DOUBLE", description="Indicator value", display_name="Value")] = None

    @classmethod
    def extract(cls, client: OECDClient, **_: Any) -> Iterator[dict[str, Any]]:
        from shenas_sources.oecd.client import DATASETS

        for dataset_key in DATASETS:
            yield from client.get_dataset(dataset_key)


TABLES = (Indicators,)
