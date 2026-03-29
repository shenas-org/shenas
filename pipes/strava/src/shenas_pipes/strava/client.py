"""Strava API client with OAuth2 token refresh."""

from __future__ import annotations

import time
from typing import Any

import httpx

API_BASE = "https://www.strava.com/api/v3"
AUTH_BASE = "https://www.strava.com/oauth"
SCOPES = "activity:read_all,profile:read_all,read"


class StravaClient:
    """HTTP client for the Strava API v3."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        client_id: str,
        client_secret: str,
        on_token_refresh: Any = None,
    ) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = expires_at
        self._client_id = client_id
        self._client_secret = client_secret
        self._on_token_refresh = on_token_refresh
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def _ensure_token(self) -> None:
        """Refresh the access token if expired."""
        if time.time() < self._expires_at - 60:
            return
        resp = self._client.post(
            f"{AUTH_BASE}/token",
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        self._expires_at = data["expires_at"]
        if self._on_token_refresh:
            self._on_token_refresh(self._access_token, self._refresh_token, self._expires_at)

    def _get(self, path: str, **params: Any) -> Any:
        self._ensure_token()
        resp = self._client.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {self._access_token}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def get_athlete(self) -> dict[str, Any]:
        """Get the authenticated athlete's profile."""
        return self._get("/athlete")

    def get_athlete_stats(self, athlete_id: int) -> dict[str, Any]:
        """Get aggregated stats for the athlete."""
        return self._get(f"/athletes/{athlete_id}/stats")

    def get_activities(self, after: int | None = None, page: int = 1, per_page: int = 200) -> list[dict[str, Any]]:
        """List the athlete's activities, newest first."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if after is not None:
            params["after"] = after
        return self._get("/athlete/activities", **params)

    @staticmethod
    def exchange_code(client_id: str, client_secret: str, code: str) -> dict[str, Any]:
        """Exchange an authorization code for tokens."""
        resp = httpx.post(
            f"{AUTH_BASE}/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def authorize_url(client_id: str, redirect_uri: str = "http://localhost:8089/exchange_token") -> str:
        """Build the OAuth2 authorization URL."""
        return (
            f"{AUTH_BASE}/authorize"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope={SCOPES}"
            f"&approval_prompt=auto"
        )
