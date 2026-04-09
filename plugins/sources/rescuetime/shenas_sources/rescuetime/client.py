"""Thin httpx wrapper for the RescueTime API."""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://www.rescuetime.com/api/v1"


class RescueTimeClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def _params(self, **extra: str) -> dict[str, str]:
        return {"key": self._api_key, "format": "json", **extra}

    def get_daily_summary(self) -> list[dict[str, Any]]:
        """Fetch the daily summary feed (all available days)."""
        resp = self._client.get("/daily_summary_feed", params=self._params())
        resp.raise_for_status()
        return resp.json()

    def get_activities(self, start_date: str, end_date: str) -> list[list[Any]]:
        """Fetch per-day per-activity breakdown.

        Returns raw row arrays; headers are:
        [Date, Time Spent (seconds), Number of People, Activity, Category, Productivity]
        """
        resp = self._client.get(
            "/data",
            params=self._params(
                perspective="rank",
                restrict_kind="activity",
                resolution_time="day",
                restrict_begin=start_date,
                restrict_end=end_date,
            ),
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("rows", [])
