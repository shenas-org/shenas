"""Thin Tile REST API client using httpx.

Tile has no official public API. This client uses the same endpoints as
the Tile mobile app, reverse-engineered from network traffic. Authentication
is email/password, which returns a session token and user UUID used for
subsequent requests.

The base URL and app metadata mimic the official Tile Android app so the
server accepts the requests.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

BASE_URL = "https://production.tile-api.com/api/v1"

# Mimic the official Tile Android app
TILE_APP_ID = "android-tile-production"
TILE_APP_VERSION = "2.131.1.4917"

# Tile API requires a persistent client UUID per device. We generate one
# per TileClient instance and register it on login. In practice, the
# stored session_token + client_uuid pair is reused across syncs.
DEFAULT_LOCALE = "en-US"


class TileClient:
    """HTTP client for the Tile REST API."""

    def __init__(self, email: str, password: str, *, client_uuid: str | None = None) -> None:
        self._email = email
        self._password = password
        self._client_uuid = client_uuid or str(uuid.uuid4())
        self._session_token: str | None = None
        self._user_uuid: str | None = None
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Tile_app_id": TILE_APP_ID,
                "Tile_app_version": TILE_APP_VERSION,
                "Tile_client_uuid": self._client_uuid,
            },
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    @property
    def client_uuid(self) -> str:
        return self._client_uuid

    def login(self) -> None:
        """Register the client and create an authenticated session."""
        # Step 1: Register client
        self._http.put(
            f"/clients/{self._client_uuid}",
            json={
                "app_id": TILE_APP_ID,
                "app_version": TILE_APP_VERSION,
                "locale": DEFAULT_LOCALE,
            },
        )

        # Step 2: Create session (login)
        resp = self._http.post(
            f"/clients/{self._client_uuid}/sessions",
            json={
                "email": self._email,
                "password": self._password,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result") or data
        self._session_token = result.get("session_token") or result.get("client_session_token")
        self._user_uuid = result.get("user", {}).get("user_uuid") or result.get("user_uuid")
        if not self._session_token or not self._user_uuid:
            msg = "Login failed: no session_token or user_uuid in response"
            raise RuntimeError(msg)

        # Update headers with session token for subsequent requests
        self._http.headers["Tile_session_token"] = self._session_token

    def _ensure_session(self) -> None:
        if not self._session_token:
            msg = "Not logged in. Call login() first."
            raise RuntimeError(msg)

    def get_tiles(self) -> list[dict[str, Any]]:
        """Fetch all registered Tile devices for the authenticated user."""
        self._ensure_session()
        resp = self._http.get(f"/users/{self._user_uuid}/user_tiles")
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result") or data
        # The API nests tiles under different keys depending on version
        if isinstance(result, dict):
            return result.get("user_tiles") or result.get("tiles") or []
        return result if isinstance(result, list) else []

    def get_tile_state(self, tile_uuid: str) -> dict[str, Any]:
        """Fetch detailed state for a single Tile device."""
        self._ensure_session()
        resp = self._http.get(f"/tiles/{tile_uuid}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("result") or data
