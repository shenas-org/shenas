"""OpenAQ source tables.

- ``DailyMeasurements`` -- daily air quality readings per station near the
  configured coordinates. One row per (date, location_id).
- ``Locations`` -- metadata for nearby monitoring stations (SCD2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core import resolve_start_date
from shenas_sources.core.table import AggregateTable, DimensionTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.openaq.client import OpenAQClient


class DailyMeasurements(AggregateTable):
    """Daily air quality measurements per monitoring station per configured place.

    A single OpenAQ station can appear under multiple places if their radii
    overlap -- the composite PK ``(place_uuid, date, location_id)`` treats
    those as distinct rows so each place's time-series stays self-contained.
    """

    class _Meta:
        name = "daily_measurements"
        display_name = "Daily Measurements"
        description = "Daily mean pollutant concentrations per monitoring station, scoped to the configured place."
        pk = ("place_uuid", "date", "location_id")

    time_at: ClassVar[str] = "date"

    place_uuid: Annotated[
        str, Field(db_type="VARCHAR", description="Place entity UUID this station was discovered from", display_name="Place")
    ] = ""
    date: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""
    location_id: Annotated[
        int, Field(db_type="INTEGER", description="OpenAQ location/station ID", display_name="Location ID")
    ] = 0
    location_name: Annotated[str, Field(db_type="VARCHAR", description="Station name", display_name="Station")] = ""
    pm25: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Daily mean PM2.5 concentration", display_name="PM2.5", unit="ug/m3"),
    ] = None
    pm10: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Daily mean PM10 concentration", display_name="PM10", unit="ug/m3"),
    ] = None
    no2: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Daily mean nitrogen dioxide", display_name="NO2", unit="ug/m3"),
    ] = None
    so2: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Daily mean sulphur dioxide", display_name="SO2", unit="ug/m3"),
    ] = None
    co: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Daily mean carbon monoxide", display_name="CO", unit="ug/m3"),
    ] = None
    o3: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Daily mean ozone", display_name="Ozone", unit="ug/m3"),
    ] = None

    @classmethod
    def extract(
        cls,
        client: OpenAQClient,
        *,
        start_date: str = "90 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        start = resolve_start_date(start_date)
        from datetime import UTC, datetime

        end = datetime.now(UTC).date().isoformat()
        yield from client.get_daily_by_location(start, end)


class Locations(DimensionTable):
    """Monitoring stations within each configured place's radius."""

    class _Meta:
        name = "locations"
        display_name = "Locations"
        description = "OpenAQ monitoring station metadata per configured place (SCD2-tracked)."
        pk = ("place_uuid", "location_id")

    place_uuid: Annotated[
        str, Field(db_type="VARCHAR", description="Place entity UUID this station was discovered from", display_name="Place")
    ] = ""
    location_id: Annotated[
        int, Field(db_type="INTEGER", description="OpenAQ location/station ID", display_name="Location ID")
    ] = 0
    name: Annotated[str, Field(db_type="VARCHAR", description="Station name", display_name="Name")] = ""
    locality: Annotated[str, Field(db_type="VARCHAR", description="City or locality name", display_name="Locality")] = ""
    country_code: Annotated[
        str, Field(db_type="VARCHAR", description="ISO 3166-1 alpha-2 country code", display_name="Country Code")
    ] = ""
    country_name: Annotated[str, Field(db_type="VARCHAR", description="Country name", display_name="Country")] = ""
    latitude: Annotated[float | None, Field(db_type="DOUBLE", description="Station latitude", display_name="Latitude")] = None
    longitude: Annotated[float | None, Field(db_type="DOUBLE", description="Station longitude", display_name="Longitude")] = (
        None
    )
    is_monitor: Annotated[
        bool, Field(db_type="BOOLEAN", description="Reference-grade monitor (vs low-cost sensor)", display_name="Is Monitor")
    ] = False
    is_mobile: Annotated[bool, Field(db_type="BOOLEAN", description="Mobile station", display_name="Is Mobile")] = False
    provider_name: Annotated[
        str, Field(db_type="VARCHAR", description="Data provider/network name", display_name="Provider")
    ] = ""
    parameters: Annotated[
        str,
        Field(db_type="VARCHAR", description="Comma-separated list of measured pollutants", display_name="Parameters"),
    ] = ""
    last_updated: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Last measurement timestamp (UTC)", display_name="Last Updated"),
    ] = None

    @classmethod
    def extract(
        cls,
        client: OpenAQClient,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        yield from client.get_locations_detail()


TABLES = (DailyMeasurements, Locations)
