"""Spotify source -- syncs listening data via OAuth2 PKCE."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Annotated, Any

from spotipy.cache_handler import CacheHandler

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source

REDIRECT_URI = "http://127.0.0.1:8090/callback"
SCOPES = "user-read-recently-played user-top-read user-library-read"

_pending_auth: dict[str, Any] = {}


class _MemoryCacheHandler(CacheHandler):
    def __init__(self) -> None:
        self.token_info: dict[str, Any] | None = None

    def get_cached_token(self) -> dict[str, Any] | None:
        return self.token_info

    def save_token_to_cache(self, token_info: dict[str, Any]) -> None:
        self.token_info = token_info


class SpotifySource(Source):
    name = "spotify"
    display_name = "Spotify"
    primary_table = "recently_played"
    description = (
        "Syncs listening data from Spotify.\n\n"
        "Uses OAuth2 PKCE flow (no client secret needed). Create an app at "
        "developer.spotify.com/dashboard with redirect URI http://127.0.0.1:8090/callback.\n\n"
        "Poll frequently (~1-2 hours) to build complete listening history."
    )

    @dataclass
    class Auth(SourceAuth):
        tokens: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description="JSON blob of OAuth2 tokens (access, refresh, client_id)",
                    category="secret",
                ),
            ]
            | None
        ) = None

    auth_instructions = (
        "Spotify requires an API application for OAuth2 access.\n"
        "\n"
        "  1. Go to https://developer.spotify.com/dashboard\n"
        "  2. Create an app (select 'Web API')\n"
        "  3. Add Redirect URI: http://127.0.0.1:8090/callback\n"
        "  4. Enter the Client ID below"
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "client_id", "prompt": "Client ID", "hide": False},
        ]

    def build_client(self) -> Any:
        import spotipy
        from spotipy.oauth2 import SpotifyPKCE

        row = self.Auth.read_row()
        if not row or not row.get("tokens"):
            msg = "No Spotify tokens found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)

        tokens = json.loads(row["tokens"])
        if "access_token" not in tokens:
            msg = "No Spotify tokens found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)

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

        pkce.get_access_token(check_cache=True)
        token_info = cache.token_info
        if not token_info:
            msg = "Token refresh failed"
            raise RuntimeError(msg)

        if token_info["access_token"] != tokens["access_token"]:
            self.Auth.write_row(
                tokens=json.dumps(
                    {
                        **tokens,
                        "access_token": token_info["access_token"],
                        "refresh_token": token_info.get("refresh_token", tokens["refresh_token"]),
                        "expires_at": token_info["expires_at"],
                    }
                ),
            )

        return spotipy.Spotify(auth=token_info["access_token"])

    def authenticate(self, credentials: dict[str, str]) -> None:

        if credentials.get("auth_complete") == "true":
            state = _pending_auth.pop("spotify", None)
            if state is None:
                msg = "No pending auth flow. Start auth again."
                raise ValueError(msg)
            thread = state["thread"]
            thread.join(timeout=120)
            if state.get("error"):
                raise RuntimeError(state["error"])
            return

        client_id = (credentials.get("client_id") or "").strip()
        if not client_id:
            msg = "client_id is required"
            raise ValueError(msg)

        from spotipy.oauth2 import SpotifyPKCE

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
        auth_cls = self.Auth

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

                def log_message(self, fmt: str, *args: Any) -> None:  # ty: ignore[invalid-method-override]
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
                auth_cls.write_row(
                    tokens=json.dumps(
                        {
                            "access_token": token_info["access_token"],
                            "refresh_token": token_info["refresh_token"],
                            "expires_at": token_info["expires_at"],
                            "client_id": client_id,
                        }
                    ),
                )
            except Exception as exc:
                state["error"] = str(exc)

        thread = threading.Thread(target=_run_flow, daemon=True)
        thread.start()
        state["thread"] = thread
        _pending_auth["spotify"] = state

        raise ValueError(f"OAUTH_URL:{auth_url}")

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.spotify.tables import TABLES, reset_track_id_cache

        reset_track_id_cache()
        return [t.to_resource(client) for t in TABLES]
