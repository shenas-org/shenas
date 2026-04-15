"""Numbeo API client.

Uses the official Numbeo API (https://www.numbeo.com/api/).
Requires a paid API key.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

BASE_URL = "https://www.numbeo.com/api"


class NumbeoClient:
    """HTTP client for the Numbeo API."""

    def __init__(self, api_key: str, cities: list[str]) -> None:
        self.api_key = api_key
        self.cities = cities
        self._http = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._http.close()

    def _get(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        all_params = {"api_key": self.api_key}
        if params:
            all_params.update(params)
        resp = self._http.get(f"{BASE_URL}/{endpoint}", params=all_params)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            msg = f"Numbeo API error: {data['error']}"
            raise RuntimeError(msg)
        return data

    def validate_key(self) -> None:
        """Validate the API key by fetching a minimal endpoint."""
        self._get("city_indices", {"query": "Berlin"})

    def get_city_indices(self, city: str) -> dict[str, Any]:
        """Fetch composite indices for a city."""
        data = self._get("city_indices", {"query": city})
        data["_city"] = data.get("name", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data

    def get_city_prices(self, city: str) -> dict[str, Any]:
        """Fetch all price items for a city (~170 items)."""
        data = self._get("city_prices", {"query": city})
        data["_city"] = data.get("city", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data

    def get_quality_of_life(self, city: str) -> dict[str, Any]:
        """Fetch quality of life sub-indices."""
        data = self._get("city_quality_of_life", {"query": city})
        data["_city"] = data.get("name", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data

    def get_city_crime(self, city: str) -> dict[str, Any]:
        """Fetch crime/safety metrics."""
        data = self._get("city_crime", {"query": city})
        data["_city"] = data.get("name", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data

    def get_city_pollution(self, city: str) -> dict[str, Any]:
        """Fetch pollution metrics."""
        data = self._get("city_pollution", {"query": city})
        data["_city"] = data.get("name", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data

    def get_city_healthcare(self, city: str) -> dict[str, Any]:
        """Fetch healthcare metrics."""
        data = self._get("city_healthcare", {"query": city})
        data["_city"] = data.get("name", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data

    def get_city_traffic(self, city: str) -> dict[str, Any]:
        """Fetch traffic metrics."""
        data = self._get("city_traffic", {"query": city})
        data["_city"] = data.get("name", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data

    def get_city_property(self, city: str) -> dict[str, Any]:
        """Fetch property market data."""
        data = self._get("city_property_market", {"query": city})
        data["_city"] = data.get("name", city)
        data["_fetched_at"] = datetime.now(UTC).date().isoformat()
        return data
