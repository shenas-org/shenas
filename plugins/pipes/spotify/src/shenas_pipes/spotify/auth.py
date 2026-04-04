"""Spotify OAuth2 token management via OS keyring.

Uses PKCE (Proof Key for Code Exchange) flow which allows http://localhost
redirect URIs. No client secret needed -- only a client ID.
"""

from __future__ import annotations

import json
import threading
from typing import Any

import spotipy
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyPKCE


class _MemoryCacheHandler(CacheHandler):
    """In-memory cache handler that captures token info for extraction."""

    def __init__(self) -> None:
        self.token_info: dict[str, Any] | None = None

    def get_cached_token(self) -> dict[str, Any] | None:
        return self.token_info

    def save_token_to_cache(self, token_info: dict[str, Any]) -> None:
        self.token_info = token_info


KEYRING_SERVICE = "shenas"
KEYRING_KEY = "spotify_tokens"
REDIRECT_URI = "http://127.0.0.1:8090/callback"
SCOPES = "user-read-recently-played user-top-read user-library-read"

AUTH_FIELDS: list[dict[str, str | bool]] = [
    {"name": "client_id", "prompt": "Client ID", "hide": False},
]

AUTH_INSTRUCTIONS = (
    "Spotify requires an API application for OAuth2 access.\n"
    "\n"
    "  1. Go to https://developer.spotify.com/dashboard\n"
    "  2. Create an app (select 'Web API')\n"
    "  3. Add Redirect URI: http://127.0.0.1:8090/callback\n"
    "  4. Enter the Client ID below"
)

# Pending auth state for the two-step REST flow
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


def build_client() -> spotipy.Spotify:
    """Build a Spotify client from stored tokens, refreshing if needed."""
    tokens = _get_stored_tokens()
    if not tokens or "access_token" not in tokens:
        raise RuntimeError("No Spotify tokens found. Configure authentication in the Auth tab.")

    cache = _MemoryCacheHandler()
    cache.token_info = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_at": tokens["expires_at"],
        "token_type": "Bearer",
        "scope": SCOPES,
    }

    pkce = SpotifyPKCE(
        client_id=tokens["client_id"],
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=cache,
    )

    # get_access_token checks cache, refreshes if expired, and saves back to cache
    pkce.get_access_token(check_cache=True)
    token_info = cache.token_info
    if not token_info:
        raise RuntimeError("Token refresh failed")

    # Persist refreshed tokens if they changed
    if token_info["access_token"] != tokens["access_token"]:
        _store_tokens(
            {
                **tokens,
                "access_token": token_info["access_token"],
                "refresh_token": token_info.get("refresh_token", tokens["refresh_token"]),
                "expires_at": token_info["expires_at"],
            }
        )

    return spotipy.Spotify(auth=token_info["access_token"])


def authenticate(credentials: dict[str, str]) -> None:
    """Run the Spotify OAuth2 PKCE flow.

    Step 1: Start a callback server in a background thread,
    raise ValueError("OAUTH_URL:...") so the REST API returns the URL.

    Step 2 (auth_complete): Wait for the background thread to finish.
    """
    if credentials.get("auth_complete") == "true":
        state = _pending_auth.pop("spotify", None)
        if state is None:
            raise ValueError("No pending auth flow. Start auth again.")
        thread = state["thread"]
        thread.join(timeout=120)
        if state.get("error"):
            raise RuntimeError(state["error"])
        return

    client_id = (credentials.get("client_id") or "").strip()

    if not client_id:
        raise ValueError("client_id is required")

    cache = _MemoryCacheHandler()
    pkce = SpotifyPKCE(
        client_id=client_id,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        open_browser=False,
        cache_handler=cache,
    )

    auth_url = pkce.get_authorize_url()
    state: dict[str, Any] = {}

    def _run_flow() -> None:
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from urllib.parse import parse_qs, urlparse

        code_result: dict[str, str] = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                qs = parse_qs(urlparse(self.path).query)
                if "code" in qs:
                    code_result["code"] = qs["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h2>Authorization complete. You can close this tab.</h2></body></html>")
                else:
                    code_result["error"] = qs.get("error", ["unknown"])[0]
                    self.send_response(400)
                    self.end_headers()

            def log_message(self, format: str, *args: Any) -> None:
                pass

        try:
            server = HTTPServer(("localhost", 8090), Handler)
            server.timeout = 120
            server.handle_request()
            server.server_close()

            if "error" in code_result:
                state["error"] = f"Authorization denied: {code_result['error']}"
                return
            if "code" not in code_result:
                state["error"] = "Authorization timed out"
                return

            pkce.get_access_token(code_result["code"], check_cache=False)
            token_info = cache.token_info
            if not token_info:
                state["error"] = "Token exchange failed -- no token received"
                return
            _store_tokens(
                {
                    "access_token": token_info["access_token"],
                    "refresh_token": token_info["refresh_token"],
                    "expires_at": token_info["expires_at"],
                    "client_id": client_id,
                }
            )
        except Exception as exc:
            state["error"] = str(exc)

    thread = threading.Thread(target=_run_flow, daemon=True)
    thread.start()
    state["thread"] = thread
    _pending_auth["spotify"] = state

    raise ValueError(f"OAUTH_URL:{auth_url}")
