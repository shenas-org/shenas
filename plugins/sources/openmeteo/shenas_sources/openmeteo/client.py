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
    """HTTP client for the Open-Meteo APIs, fans out across N places.

    Each *place* is a ``(place_uuid, latitude, longitude)`` tuple resolved
    from a place entity row via the entity index. Both ``get_daily_weather`` and
    ``get_hourly_air_quality`` iterate over the configured places and tag
    every returned row with its ``place_uuid`` so downstream merge
    semantics stay per-place-per-date.
    """

    def __init__(self, places: list[tuple[str, float, float]]) -> None:
        self.places = places
        self._http = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._http.close()

    def get_daily_weather(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch daily weather for each configured place. Dates are ISO (YYYY-MM-DD)."""
        out: list[dict[str, Any]] = []
        for place_uuid, lat, lon in self.places:
            resp = self._http.get(
                ARCHIVE_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": DAILY_WEATHER_PARAMS,
                    "timezone": "UTC",
                },
            )
            resp.raise_for_status()
            daily = resp.json().get("daily", {})
            for row in _columnar_to_rows(daily):
                row["place_uuid"] = place_uuid
                out.append(row)
        return out

    def get_hourly_air_quality(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch hourly air quality for each place and aggregate to daily."""
        out: list[dict[str, Any]] = []
        for place_uuid, lat, lon in self.places:
            resp = self._http.get(
                AIR_QUALITY_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": start_date,
                    "end_date": end_date,
                    "hourly": HOURLY_AQ_PARAMS,
                    "timezone": "UTC",
                },
            )
            resp.raise_for_status()
            hourly = resp.json().get("hourly", {})
            for row in _aggregate_hourly_to_daily(hourly):
                row["place_uuid"] = place_uuid
                out.append(row)
        return out


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
