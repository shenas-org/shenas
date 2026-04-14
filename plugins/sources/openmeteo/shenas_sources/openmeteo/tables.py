"""Open-Meteo source tables.

- ``DailyWeather`` -- daily weather observations from the Archive API (ERA5 reanalysis).
  Wind speed converted from km/h to m/s, snowfall from cm to mm.
- ``DailyAirQuality`` -- daily air quality from hourly measurements, aggregated to
  daily mean (pollutants) and daily max (AQI indices).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core import resolve_start_date
from shenas_sources.core.table import AggregateTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.openmeteo.client import OpenMeteoClient


class DailyWeather(AggregateTable):
    """Daily weather observations from Open-Meteo (ERA5 reanalysis, back to 1940)."""

    class _Meta:
        name = "daily_weather"
        display_name = "Daily Weather"
        description = "Daily weather observations per place: temperature, precipitation, wind, sunshine."
        pk = ("place_uuid", "date")

    time_at: ClassVar[str] = "date"

    place_uuid: Annotated[
        str,
        Field(db_type="VARCHAR", description="Place entity UUID this observation belongs to", display_name="Place"),
    ] = ""
    date: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""
    temp_max_degc: Annotated[
        float | None, Field(db_type="DOUBLE", description="Maximum temperature at 2m", display_name="Max Temp", unit="degC")
    ] = None
    temp_min_degc: Annotated[
        float | None, Field(db_type="DOUBLE", description="Minimum temperature at 2m", display_name="Min Temp", unit="degC")
    ] = None
    temp_mean_degc: Annotated[
        float | None, Field(db_type="DOUBLE", description="Mean temperature at 2m", display_name="Mean Temp", unit="degC")
    ] = None
    apparent_temp_max_degc: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Maximum apparent (feels-like) temperature",
            display_name="Max Feels-Like",
            unit="degC",
        ),
    ] = None
    apparent_temp_min_degc: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Minimum apparent (feels-like) temperature",
            display_name="Min Feels-Like",
            unit="degC",
        ),
    ] = None
    precipitation_mm: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Total precipitation (rain + snow)", display_name="Precipitation", unit="mm"),
    ] = None
    rain_mm: Annotated[float | None, Field(db_type="DOUBLE", description="Rainfall", display_name="Rain", unit="mm")] = None
    snowfall_mm: Annotated[
        float | None, Field(db_type="DOUBLE", description="Snowfall (water equivalent)", display_name="Snowfall", unit="mm")
    ] = None
    wind_speed_max_ms: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Maximum wind speed at 10m", display_name="Max Wind Speed", unit="m/s"),
    ] = None
    wind_gusts_max_ms: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Maximum wind gusts at 10m", display_name="Max Wind Gusts", unit="m/s"),
    ] = None
    wind_direction_dominant_deg: Annotated[
        float | None, Field(db_type="DOUBLE", description="Dominant wind direction", display_name="Wind Direction", unit="deg")
    ] = None
    sunshine_duration_s: Annotated[
        float | None, Field(db_type="DOUBLE", description="Sunshine duration", display_name="Sunshine", unit="s")
    ] = None
    daylight_duration_s: Annotated[
        float | None, Field(db_type="DOUBLE", description="Daylight duration", display_name="Daylight", unit="s")
    ] = None
    uv_index_max: Annotated[
        float | None, Field(db_type="DOUBLE", description="Maximum UV index", display_name="Max UV Index")
    ] = None
    humidity_mean_pct: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Mean relative humidity at 2m", display_name="Mean Humidity", unit="percent"),
    ] = None
    pressure_msl_mean_hpa: Annotated[
        float | None, Field(db_type="DOUBLE", description="Mean sea-level pressure", display_name="Mean Pressure", unit="hPa")
    ] = None

    @classmethod
    def extract(
        cls,
        client: OpenMeteoClient,
        *,
        start_date: str = "365 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        start = resolve_start_date(start_date)
        from datetime import UTC, datetime

        end = datetime.now(UTC).date().isoformat()
        for row in client.get_daily_weather(start, end):
            yield {
                "place_uuid": row["place_uuid"],
                "date": row["date"],
                "temp_max_degc": row.get("temperature_2m_max"),
                "temp_min_degc": row.get("temperature_2m_min"),
                "temp_mean_degc": row.get("temperature_2m_mean"),
                "apparent_temp_max_degc": row.get("apparent_temperature_max"),
                "apparent_temp_min_degc": row.get("apparent_temperature_min"),
                "precipitation_mm": row.get("precipitation_sum"),
                "rain_mm": row.get("rain_sum"),
                "snowfall_mm": _cm_to_mm(row.get("snowfall_sum")),
                "wind_speed_max_ms": _kmh_to_ms(row.get("wind_speed_10m_max")),
                "wind_gusts_max_ms": _kmh_to_ms(row.get("wind_gusts_10m_max")),
                "wind_direction_dominant_deg": row.get("wind_direction_10m_dominant"),
                "sunshine_duration_s": row.get("sunshine_duration"),
                "daylight_duration_s": row.get("daylight_duration"),
                "uv_index_max": row.get("uv_index_max"),
                "humidity_mean_pct": row.get("relative_humidity_2m_mean"),
                "pressure_msl_mean_hpa": row.get("pressure_msl_mean"),
            }


class DailyAirQuality(AggregateTable):
    """Daily air quality from Open-Meteo (CAMS global reanalysis)."""

    class _Meta:
        name = "daily_air_quality"
        display_name = "Daily Air Quality"
        description = "Daily air quality per place: PM2.5, PM10, NO2, SO2, CO, O3, AQI indices."
        pk = ("place_uuid", "date")

    time_at: ClassVar[str] = "date"

    place_uuid: Annotated[
        str,
        Field(db_type="VARCHAR", description="Place entity UUID this observation belongs to", display_name="Place"),
    ] = ""
    date: Annotated[str, Field(db_type="DATE", description="Calendar date", display_name="Date")] = ""
    pm25: Annotated[
        float | None, Field(db_type="DOUBLE", description="Mean PM2.5 concentration", display_name="PM2.5", unit="ug/m3")
    ] = None
    pm10: Annotated[
        float | None, Field(db_type="DOUBLE", description="Mean PM10 concentration", display_name="PM10", unit="ug/m3")
    ] = None
    no2: Annotated[
        float | None, Field(db_type="DOUBLE", description="Mean nitrogen dioxide", display_name="NO2", unit="ug/m3")
    ] = None
    so2: Annotated[
        float | None, Field(db_type="DOUBLE", description="Mean sulphur dioxide", display_name="SO2", unit="ug/m3")
    ] = None
    co: Annotated[
        float | None, Field(db_type="DOUBLE", description="Mean carbon monoxide", display_name="CO", unit="ug/m3")
    ] = None
    o3: Annotated[float | None, Field(db_type="DOUBLE", description="Mean ozone", display_name="Ozone", unit="ug/m3")] = None
    european_aqi: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="European Air Quality Index (daily max)", display_name="European AQI"),
    ] = None
    us_aqi: Annotated[
        float | None, Field(db_type="DOUBLE", description="US Air Quality Index (daily max)", display_name="US AQI")
    ] = None

    @classmethod
    def extract(
        cls,
        client: OpenMeteoClient,
        *,
        start_date: str = "365 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        start = resolve_start_date(start_date)
        from datetime import UTC, datetime

        end = datetime.now(UTC).date().isoformat()
        for row in client.get_hourly_air_quality(start, end):
            yield {
                "place_uuid": row["place_uuid"],
                "date": row["date"],
                "pm25": row.get("pm2_5"),
                "pm10": row.get("pm10"),
                "no2": row.get("nitrogen_dioxide"),
                "so2": row.get("sulphur_dioxide"),
                "co": row.get("carbon_monoxide"),
                "o3": row.get("ozone"),
                "european_aqi": row.get("european_aqi"),
                "us_aqi": row.get("us_aqi"),
            }


TABLES = (DailyWeather, DailyAirQuality)


def _kmh_to_ms(val: float | None) -> float | None:
    """Convert km/h to m/s."""
    return round(val / 3.6, 2) if val is not None else None


def _cm_to_mm(val: float | None) -> float | None:
    """Convert cm to mm."""
    return round(val * 10, 1) if val is not None else None
