"""OpenAQ API v3 client.

Two-step workflow: discover locations near coordinates, then fetch daily
measurements per sensor. Results are aggregated to daily granularity.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

BASE_URL = "https://api.openaq.org/v3"

# Core pollutant parameter names we care about
CORE_PARAMETERS = ("pm25", "pm10", "no2", "so2", "co", "o3")


class OpenAQClient:
    """HTTP client for the OpenAQ v3 API."""

    def __init__(
        self,
        api_key: str,
        latitude: float,
        longitude: float,
        radius_m: int = 25000,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.radius_m = min(radius_m, 25000)
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"X-API-Key": api_key},
            timeout=60.0,
        )
        self._location_ids: list[int] | None = None

    def close(self) -> None:
        self._http.close()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET with rate-limit retry (60 req/min)."""
        resp = self._http.get(path, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            time.sleep(retry_after)
            resp = self._http.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_parameters(self) -> list[dict[str, Any]]:
        """Fetch available parameters (used for auth validation)."""
        data = self._get("/parameters", {"limit": 10})
        return data.get("results", [])

    def get_locations(self) -> list[dict[str, Any]]:
        """Find monitoring stations near the configured coordinates."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self._get(
                "/locations",
                {
                    "coordinates": f"{self.latitude},{self.longitude}",
                    "radius": self.radius_m,
                    "limit": 100,
                    "page": page,
                },
            )
            batch = data.get("results", [])
            results.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return results

    def get_location_ids(self) -> list[int]:
        """Cached list of location IDs near the configured coordinates."""
        if self._location_ids is None:
            locations = self.get_locations()
            self._location_ids = [loc["id"] for loc in locations]
        return self._location_ids

    def get_sensors_for_location(self, location_id: int) -> list[dict[str, Any]]:
        """Get all sensors at a given location."""
        data = self._get(f"/locations/{location_id}/sensors", {"limit": 100})
        return data.get("results", [])

    def get_daily_measurements(
        self,
        sensor_id: int,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch daily-aggregated measurements for a sensor."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self._get(
                f"/sensors/{sensor_id}/measurements",
                {
                    "datetime_from": f"{start_date}T00:00:00Z",
                    "datetime_to": f"{end_date}T23:59:59Z",
                    "period_name": "day",
                    "limit": 1000,
                    "page": page,
                },
            )
            batch = data.get("results", [])
            results.extend(batch)
            if len(batch) < 1000:
                break
            page += 1
        return results

    def get_daily_by_location(
        self,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """Fetch daily measurements for all nearby locations, pivoted by date.

        Returns one row per (date, location_id) with columns for each pollutant.
        """
        location_ids = self.get_location_ids()
        # date -> location_id -> {param: value}
        by_date_loc: dict[str, dict[int, dict[str, float | None]]] = {}
        location_meta: dict[int, dict[str, Any]] = {}

        for loc_id in location_ids:
            sensors = self.get_sensors_for_location(loc_id)
            for sensor in sensors:
                param_name = sensor.get("parameter", {}).get("name", "")
                if param_name not in CORE_PARAMETERS:
                    continue
                sensor_id = sensor["id"]
                loc_name = sensor.get("location", {}).get("name") or str(loc_id)
                if loc_id not in location_meta:
                    location_meta[loc_id] = {"name": loc_name}

                measurements = self.get_daily_measurements(sensor_id, start_date, end_date)
                for m in measurements:
                    period = m.get("period", {})
                    dt_from = period.get("datetimeFrom", {}).get("utc", "")
                    date = dt_from[:10] if dt_from else ""
                    if not date:
                        continue
                    summary = m.get("summary", {})
                    avg = summary.get("avg")
                    if avg is None:
                        avg = m.get("value")

                    by_date_loc.setdefault(date, {}).setdefault(loc_id, {})[param_name] = avg

        rows: list[dict[str, Any]] = []
        for date in sorted(by_date_loc):
            for loc_id, params in by_date_loc[date].items():
                row: dict[str, Any] = {
                    "date": date,
                    "location_id": loc_id,
                    "location_name": location_meta.get(loc_id, {}).get("name", str(loc_id)),
                }
                for p in CORE_PARAMETERS:
                    row[p] = params.get(p)
                rows.append(row)
        return rows

    def get_locations_detail(self) -> list[dict[str, Any]]:
        """Return location metadata for nearby stations."""
        locations = self.get_locations()
        rows: list[dict[str, Any]] = []
        for loc in locations:
            coords = loc.get("coordinates", {})
            country = loc.get("country", {})
            provider = loc.get("provider", {})
            sensor_params = []
            for s in loc.get("sensors", []):
                p = s.get("parameter", {})
                if p.get("name"):
                    sensor_params.append(p["name"])
            rows.append(
                {
                    "location_id": loc["id"],
                    "name": loc.get("name", ""),
                    "locality": loc.get("locality") or "",
                    "country_code": country.get("code", ""),
                    "country_name": country.get("name", ""),
                    "latitude": coords.get("latitude"),
                    "longitude": coords.get("longitude"),
                    "is_monitor": loc.get("isMonitor", False),
                    "is_mobile": loc.get("isMobile", False),
                    "provider_name": provider.get("name", ""),
                    "parameters": ",".join(sorted(set(sensor_params))),
                    "last_updated": loc.get("datetimeLast", {}).get("utc"),
                }
            )
        return rows
