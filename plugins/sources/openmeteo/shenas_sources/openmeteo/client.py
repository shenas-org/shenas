"""Open-Meteo API client.

Uses the Archive API for historical weather data and the Air Quality API
for pollutant and pollen data. No API key required.
"""

from __future__ import annotations

from typing import Any

import httpx

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

DAILY_WEATHER_PARAMS = (
    "temperature_2m_max,"
    "temperature_2m_min,"
    "temperature_2m_mean,"
    "apparent_temperature_max,"
    "apparent_temperature_min,"
    "precipitation_sum,"
    "rain_sum,"
    "snowfall_sum,"
    "wind_speed_10m_max,"
    "wind_gusts_10m_max,"
    "wind_direction_10m_dominant,"
    "sunshine_duration,"
    "daylight_duration,"
    "uv_index_max,"
    "relative_humidity_2m_mean,"
    "pressure_msl_mean"
)

HOURLY_AQ_PARAMS = "pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone,european_aqi,us_aqi"


class OpenMeteoClient:
    """HTTP client for the Open-Meteo APIs."""

    def __init__(self, latitude: float, longitude: float) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self._http = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._http.close()

    def get_daily_weather(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch daily weather data. Dates are ISO format (YYYY-MM-DD)."""
        resp = self._http.get(
            ARCHIVE_URL,
            params={
                "latitude": self.latitude,
                "longitude": self.longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": DAILY_WEATHER_PARAMS,
                "timezone": "UTC",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        return _columnar_to_rows(daily)

    def get_hourly_air_quality(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch hourly air quality data and aggregate to daily."""
        resp = self._http.get(
            AIR_QUALITY_URL,
            params={
                "latitude": self.latitude,
                "longitude": self.longitude,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": HOURLY_AQ_PARAMS,
                "timezone": "UTC",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        hourly = data.get("hourly", {})
        return _aggregate_hourly_to_daily(hourly)


def _columnar_to_rows(columnar: dict[str, list]) -> list[dict[str, Any]]:
    """Convert Open-Meteo's columnar format to row-oriented dicts."""
    times = columnar.get("time", [])
    keys = [k for k in columnar if k != "time"]
    rows: list[dict[str, Any]] = []
    for i, date in enumerate(times):
        row: dict[str, Any] = {"date": date}
        for key in keys:
            val = columnar[key][i]
            row[key] = val
        rows.append(row)
    return rows


def _aggregate_hourly_to_daily(hourly: dict[str, list]) -> list[dict[str, Any]]:
    """Aggregate hourly air quality readings to daily means/maxes."""
    times = hourly.get("time", [])
    keys = [k for k in hourly if k != "time"]
    by_date: dict[str, dict[str, list[float]]] = {}
    for i, ts in enumerate(times):
        date = ts[:10]
        if date not in by_date:
            by_date[date] = {k: [] for k in keys}
        for key in keys:
            val = hourly[key][i]
            if val is not None:
                by_date[date][key].append(val)

    rows: list[dict[str, Any]] = []
    for date in sorted(by_date):
        row: dict[str, Any] = {"date": date}
        for key in keys:
            vals = by_date[date][key]
            if not vals:
                row[key] = None
            elif key in ("european_aqi", "us_aqi"):
                row[key] = max(vals)
            else:
                row[key] = round(sum(vals) / len(vals), 2)
        rows.append(row)
    return rows
