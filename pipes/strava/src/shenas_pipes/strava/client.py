"""Strava API client wrapper around stravalib with token refresh callback."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from stravalib import Client

AUTH_BASE = "https://www.strava.com/oauth"
SCOPES = "activity:read_all,profile:read_all,read"


def build_strava_client(
    access_token: str,
    refresh_token: str,
    expires_at: int,
    client_id: str,
    client_secret: str,
    on_token_refresh: Callable[[str, str, int], None] | None = None,
) -> Client:
    """Create a stravalib Client and refresh the token if expired."""
    import time

    client = Client(access_token=access_token)

    if time.time() >= expires_at - 60:
        token_response = client.refresh_access_token(
            client_id=int(client_id),
            client_secret=client_secret,
            refresh_token=refresh_token,
        )
        client.access_token = token_response["access_token"]
        new_refresh = token_response["refresh_token"]
        new_expires = token_response["expires_at"]
        if on_token_refresh:
            on_token_refresh(token_response["access_token"], new_refresh, new_expires)

    return client


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


def exchange_code(client_id: str, client_secret: str, code: str) -> dict[str, Any]:
    """Exchange an authorization code for tokens via stravalib."""
    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=int(client_id),
        client_secret=client_secret,
        code=code,
    )
    return dict(token_response)
