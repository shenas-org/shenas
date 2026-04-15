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

# Mimic the official Tile iOS app, matching the upstream pytile reference
# client (https://github.com/bachya/pytile). Tile's reverse-engineered API
# is picky about header casing and the api-version header -- match pytile
# exactly to keep working past server-side tightening.
TILE_API_VERSION = "1.0"
TILE_APP_ID = "ios-tile-production"
TILE_APP_VERSION = "2.89.1.4774"
TILE_USER_AGENT = "Tile/4774 CFNetwork/1312 Darwin/21.0.0"

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
                "User-Agent": TILE_USER_AGENT,
                "tile_api_version": TILE_API_VERSION,
                "tile_app_id": TILE_APP_ID,
                "tile_app_version": TILE_APP_VERSION,
                "tile_client_uuid": self._client_uuid,
            },
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    @property
    def client_uuid(self) -> str:
        return self._client_uuid

    def login(self) -> None:
        """Register the client and create an authenticated session.

        Tile's mobile-app endpoints both expect ``application/x-www-form-urlencoded``
        bodies (sending JSON gets rejected with HTTP 415), so use ``data=``.
        Session continuity is handled by HTTP cookies which httpx persists on
        ``self._http`` automatically -- there is no separate session token in
        the response body, contrary to older docs. Only ``user_uuid`` is
        captured here, mirroring the upstream pytile reference.
        """
        # Step 1: Register client
        self._http.put(
            f"/clients/{self._client_uuid}",
            data={
                "app_id": TILE_APP_ID,
                "app_version": TILE_APP_VERSION,
                "locale": DEFAULT_LOCALE,
            },
        )

        # Step 2: Create session (login)
        resp = self._http.post(
            f"/clients/{self._client_uuid}/sessions",
            data={
                "email": self._email,
                "password": self._password,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result") or data
        if isinstance(result, dict):
            user = result.get("user") or {}
            self._user_uuid = (user.get("user_uuid") if isinstance(user, dict) else None) or result.get("user_uuid")
            self._session_token = (
                result.get("session_token") or result.get("client_session_token") or result.get("session_expiration_timestamp")
            )
        if not self._user_uuid:
            # Surface the actual response shape to make debugging future
            # API changes possible without server-side credentials.
            shape = sorted(result.keys()) if isinstance(result, dict) else type(result).__name__
            msg = f"Login failed: no user_uuid in response (response keys: {shape})"
            raise RuntimeError(msg)
        # Mark session as established so _ensure_session can proceed; the
        # actual auth is now carried by httpx's cookie jar.
        self._session_token = self._session_token or "cookie"

    def _ensure_session(self) -> None:
        if not self._user_uuid:
            msg = "Not logged in. Call login() first."
            raise RuntimeError(msg)

    def get_tiles(self) -> list[dict[str, Any]]:
        """Fetch all registered Tile devices with full details.

        Mirrors the upstream pytile flow: ``GET /tiles/tile_states`` returns
        only IDs (and a few low-detail fields), so we iterate and call
        ``GET /tiles/{tile_uuid}`` on each one to pull the full record
        (name, firmware, hardware, last_tile_state with battery / location /
        connection / etc.).

        Tile Labels and similar items respond with HTTP 412 on the detail
        endpoint -- they have no additional info, so we keep the bare entry
        from the list response instead of dropping them.
        """
        self._ensure_session()
        resp = self._http.get("/tiles/tile_states")
        resp.raise_for_status()
        data = resp.json()
        states_result = data.get("result") or data
        states: list[dict[str, Any]] = []
        if isinstance(states_result, list):
            states = states_result
        elif isinstance(states_result, dict):
            states = states_result.get("tile_states") or states_result.get("tiles") or []

        tiles: list[dict[str, Any]] = []
        for state in states:
            if not isinstance(state, dict):
                continue
            tile_uuid = state.get("tile_id") or state.get("tile_uuid") or state.get("uuid")
            if not tile_uuid:
                continue
            try:
                detail = self.get_tile_state(tile_uuid)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 412:
                    # Tile Labels return 412 with no additional details.
                    tiles.append({"uuid": tile_uuid, **state})
                    continue
                raise
            # Merge the list-level state under the detailed record so the
            # last_tile_state path (used for location / battery) is present
            # if the detail endpoint omits it.
            merged = {**state, **detail}
            merged.setdefault("uuid", tile_uuid)
            tiles.append(merged)
        return tiles

    def get_tile_state(self, tile_uuid: str) -> dict[str, Any]:
        """Fetch detailed state for a single Tile device."""
        self._ensure_session()
        resp = self._http.get(f"/tiles/{tile_uuid}")
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result") or data
        return result if isinstance(result, dict) else {}
