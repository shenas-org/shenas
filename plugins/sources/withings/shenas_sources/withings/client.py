"""Withings Health API client using httpx.

All Withings data endpoints use POST with an ``action`` parameter.
Responses follow the shape ``{"status": 0, "body": {...}}`` where
status 0 means success.

Measurement values from ``getmeas`` require scaling:
``real_value = value * 10 ** unit`` (e.g. value=72345, unit=-3 -> 72.345 kg).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

BASE_URL = "https://wbsapi.withings.net"
TOKEN_URL = f"{BASE_URL}/v2/oauth2"
AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"

# Measurement type codes returned by getmeas
MEASURE_TYPES: dict[int, str] = {
    1: "weight_kg",
    5: "fat_free_mass_kg",
    6: "fat_ratio_pct",
    8: "fat_mass_kg",
    9: "diastolic_bp",
    10: "systolic_bp",
    11: "heart_pulse",
    54: "spo2_pct",
    71: "body_temperature_degc",
    76: "muscle_mass_kg",
    88: "bone_mass_kg",
}


class WithingsClient:
    """HTTP client for the Withings Health API."""

    def __init__(self, access_token: str) -> None:
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    def _post(self, path: str, **params: Any) -> dict[str, Any]:
        resp = self._http.post(path, data=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 0:
            msg = f"Withings API error: status={data.get('status')}, error={data.get('error')}"
            raise RuntimeError(msg)
        return data.get("body") or {}

    def get_measurements(self, start_epoch: int, end_epoch: int) -> list[dict[str, Any]]:
        """Fetch body measurements (weight, fat, BP, etc.).

        Returns flattened measurement groups with type codes mapped to
        named columns and values scaled by their unit exponent.
        """
        body = self._post(
            "/measure",
            action="getmeas",
            startdate=str(start_epoch),
            enddate=str(end_epoch),
            meastypes=",".join(str(t) for t in MEASURE_TYPES),
        )
        groups = body.get("measuregrps") or []
        rows: list[dict[str, Any]] = []
        for grp in groups:
            row: dict[str, Any] = {
                "grpid": grp["grpid"],
                "created_at": datetime.fromtimestamp(grp["date"]).isoformat(),  # noqa: DTZ006
            }
            for m in grp.get("measures") or []:
                col = MEASURE_TYPES.get(m["type"])
                if col:
                    row[col] = m["value"] * 10 ** m["unit"]
            rows.append(row)
        return rows

    def get_sleep_summary(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch daily sleep summaries.

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        """
        body = self._post(
            "/v2/sleep",
            action="getsummary",
            startdateymd=start_date,
            enddateymd=end_date,
        )
        return body.get("series") or []

    def get_activity(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch daily activity summaries.

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        """
        body = self._post(
            "/v2/measure",
            action="getactivity",
            startdateymd=start_date,
            enddateymd=end_date,
        )
        return body.get("activities") or []

    def get_devices(self) -> list[dict[str, Any]]:
        """Fetch connected Withings devices."""
        body = self._post("/v2/user", action="getdevice")
        return body.get("devices") or []

    @staticmethod
    def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange an authorization code for tokens."""
        resp = httpx.post(
            TOKEN_URL,
            data={
                "action": "requesttoken",
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 0:
            msg = f"Token exchange failed: {data}"
            raise RuntimeError(msg)
        return data.get("body") or {}

    @staticmethod
    def refresh_tokens(client_id: str, client_secret: str, refresh_token: str) -> dict[str, Any]:
        """Refresh an expired access token."""
        resp = httpx.post(
            TOKEN_URL,
            data={
                "action": "requesttoken",
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 0:
            msg = f"Token refresh failed: {data}"
            raise RuntimeError(msg)
        return data.get("body") or {}
