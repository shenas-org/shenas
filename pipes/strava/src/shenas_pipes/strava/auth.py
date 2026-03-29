"""Strava OAuth2 token management via OS keyring.

Auth flow:
1. User provides client_id and client_secret (from strava.com/settings/api)
2. We open Strava's authorize URL in the browser
3. User authorizes, Strava redirects to localhost with a code
4. We exchange the code for access + refresh tokens (stored in keyring)
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from shenas_pipes.strava.client import authorize_url, exchange_code

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "strava_tokens"
CALLBACK_PORT = 8089

AUTH_FIELDS: list[dict[str, str | bool]] = [
    {"name": "client_id", "prompt": "Client ID", "hide": False},
    {"name": "client_secret", "prompt": "Client secret", "hide": True},
]

AUTH_INSTRUCTIONS = (
    "Strava requires an API application for OAuth2 access.\n"
    "\n"
    "  1. Go to https://www.strava.com/settings/api\n"
    "  2. Create an app (set Authorization Callback Domain to 'localhost')\n"
    "  3. Enter the Client ID and Client Secret below"
)

# Shared state for pending OAuth flows (server-side)
_pending_auth: dict[str, Any] = {}


def _get_stored_tokens() -> dict[str, Any] | None:
    """Read tokens from OS keyring."""
    try:
        import keyring

        data = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def _store_tokens(tokens: dict[str, Any]) -> None:
    """Write tokens to OS keyring."""
    import keyring

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        pass
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, json.dumps(tokens))


def _on_token_refresh(access_token: str, refresh_token: str, expires_at: int) -> None:
    """Callback to persist refreshed tokens."""
    stored = _get_stored_tokens() or {}
    stored["access_token"] = access_token
    stored["refresh_token"] = refresh_token
    stored["expires_at"] = expires_at
    _store_tokens(stored)


def build_client() -> Any:
    """Build a stravalib Client from stored tokens."""
    from shenas_pipes.strava.client import build_strava_client

    tokens = _get_stored_tokens()
    if not tokens or "access_token" not in tokens:
        raise RuntimeError("No Strava tokens found. Run 'shenasctl pipe strava auth' first.")
    return build_strava_client(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_at=tokens["expires_at"],
        client_id=tokens["client_id"],
        client_secret=tokens["client_secret"],
        on_token_refresh=_on_token_refresh,
    )


def _wait_for_code(timeout: int = 120) -> str:
    """Start a local HTTP server and wait for the OAuth callback with the auth code."""
    result: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            qs = parse_qs(urlparse(self.path).query)
            if "code" in qs:
                result["code"] = qs["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h2>Authorization complete. You can close this tab.</h2></body></html>")
            else:
                error = qs.get("error", ["unknown"])[0]
                result["error"] = error
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Authorization failed: {error}".encode())

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = HTTPServer(("localhost", CALLBACK_PORT), Handler)
    server.timeout = timeout
    server.handle_request()
    server.server_close()

    if "error" in result:
        raise ValueError(f"Authorization denied: {result['error']}")
    if "code" not in result:
        raise ValueError("Authorization timed out -- no callback received")
    return result["code"]


def authenticate(credentials: dict[str, str]) -> None:
    """Run the Strava OAuth2 flow.

    Step 1 (initial call): Starts a callback server in a background thread,
    then raises ValueError("OAUTH_URL:...") so the REST API returns the URL.

    Step 2 (auth_complete call): Waits for the background thread to finish.
    """
    if credentials.get("auth_complete") == "true":
        state = _pending_auth.pop("strava", None)
        if state is None:
            raise ValueError("No pending auth flow. Start auth again.")
        thread = state["thread"]
        thread.join(timeout=120)
        if state.get("error"):
            raise RuntimeError(state["error"])
        return

    client_id = (credentials.get("client_id") or "").strip()
    client_secret = (credentials.get("client_secret") or "").strip()

    if not client_id or not client_secret:
        raise ValueError("client_id and client_secret are required")

    auth_url = authorize_url(client_id)

    state: dict[str, Any] = {}

    def _run_flow() -> None:
        try:
            code = _wait_for_code()
            token_data = exchange_code(client_id, client_secret, code)
            _store_tokens(
                {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data["refresh_token"],
                    "expires_at": token_data["expires_at"],
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "athlete_id": token_data.get("athlete", {}).get("id"),
                }
            )
        except Exception as exc:
            state["error"] = str(exc)

    thread = threading.Thread(target=_run_flow, daemon=True)
    thread.start()
    state["thread"] = thread
    _pending_auth["strava"] = state

    raise ValueError(f"OAUTH_URL:{auth_url}")
