"""Withings Health API client using httpx.

All Withings data endpoints use POST with an ``action`` parameter.
Responses follow the shape ``{"status": 0, "body": {...}}`` where
status 0 means success.

Measurement values from ``getmeas`` require scaling:
``real_value = value * 10 ** unit`` (e.g. value=72345, unit=-3 -> 72.345 kg).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

log = logging.getLogger("shenas.source.withings")

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
        Paginates automatically via the ``more``/``offset`` fields.
        """
        log.info(
            "Fetching measurements from %s to %s",
            datetime.fromtimestamp(start_epoch).isoformat()[:10],  # noqa: DTZ006
            datetime.fromtimestamp(end_epoch).isoformat()[:10],  # noqa: DTZ006
        )
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            params: dict[str, str] = {
                "action": "getmeas",
                "startdate": str(start_epoch),
                "enddate": str(end_epoch),
            }
            if offset:
                params["offset"] = str(offset)
            body = self._post("/measure", **params)
            page_groups = body.get("measuregrps") or []
            log.info("Got %d measurement groups (more=%s, offset=%s)", len(page_groups), body.get("more"), body.get("offset"))
            for grp in page_groups:
                row: dict[str, Any] = {
                    "grpid": grp["grpid"],
                    "created_at": datetime.fromtimestamp(grp["date"]).isoformat(),  # noqa: DTZ006
                }
                for measurement in grp.get("measures") or []:
                    col = MEASURE_TYPES.get(measurement["type"])
                    if col:
                        row[col] = measurement["value"] * 10 ** measurement["unit"]
                    else:
                        log.debug("Unknown measure type %d, value=%s", measurement["type"], measurement["value"])
                rows.append(row)
            if not body.get("more"):
                break
            offset = body.get("offset", 0)
        log.info("Total measurements fetched: %d", len(rows))
        return rows

    def get_sleep_summary(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch daily sleep summaries.

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        """
        results: list[dict[str, Any]] = []
        offset = 0
        while True:
            params: dict[str, str] = {"action": "getsummary", "startdateymd": start_date, "enddateymd": end_date}
            if offset:
                params["offset"] = str(offset)
            body = self._post("/v2/sleep", **params)
            results.extend(body.get("series") or [])
            if not body.get("more"):
                break
            offset = body.get("offset", 0)
        return results

    def get_activity(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch daily activity summaries.

        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        """
        results: list[dict[str, Any]] = []
        offset = 0
        while True:
            params: dict[str, str] = {"action": "getactivity", "startdateymd": start_date, "enddateymd": end_date}
            if offset:
                params["offset"] = str(offset)
            body = self._post("/v2/measure", **params)
            results.extend(body.get("activities") or [])
            if not body.get("more"):
                break
            offset = body.get("offset", 0)
        return results

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
            error_detail = data.get("error") or f"status {data.get('status')}"
            msg = f"Token refresh failed: {error_detail}. Please re-authenticate."
            raise RuntimeError(msg)
        return data.get("body") or {}
