"""Spotify source -- listening history via OAuth2 PKCE."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source

log = logging.getLogger(__name__)

SCOPES = "user-read-recently-played user-top-read user-library-read"

# Pending PKCE state for the redirect flow
_pending_pkce: dict[str, Any] = {}


class _MemoryCacheHandler:
    """In-memory token cache for SpotifyPKCE."""

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
        "developer.spotify.com/dashboard.\n\n"
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
        "  3. In the app settings, add a Redirect URI that matches your\n"
        "     shenas URL + /api/auth/source/spotify/callback\n"
        "     (e.g. http://localhost:5173/api/auth/source/spotify/callback)\n"
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

        redirect_uri = tokens.get("redirect_uri", "http://localhost")
        pkce = SpotifyPKCE(
            client_id=tokens["client_id"],
            redirect_uri=redirect_uri,
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

    # -- OAuth redirect flow --

    @property
    def supports_oauth_redirect(self) -> bool:
        return True

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:
        from spotipy.oauth2 import SpotifyPKCE

        client_id = (credentials or {}).get("client_id", "").strip()
        if not client_id:
            msg = "client_id is required"
            raise ValueError(msg)

        cache = _MemoryCacheHandler()
        pkce = SpotifyPKCE(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=SCOPES,
            open_browser=False,
            cache_handler=cache,
        )

        auth_url = pkce.get_authorize_url()
        _pending_pkce[self.name] = {
            "pkce": pkce,
            "cache": cache,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        }
        log.info("Spotify OAuth started, redirect_uri=%s", redirect_uri)
        return auth_url

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:  # noqa: ARG002
        entry = _pending_pkce.pop(self.name, None)
        if not entry:
            msg = "No pending Spotify OAuth flow. Start auth again."
            raise RuntimeError(msg)

        pkce = entry["pkce"]
        cache = entry["cache"]
        client_id = entry["client_id"]
        redirect_uri = entry["redirect_uri"]

        pkce.get_access_token(code, check_cache=False)
        token_info = cache.token_info
        if not token_info:
            msg = "Token exchange failed -- no token received"
            raise RuntimeError(msg)

        self.Auth.write_row(
            tokens=json.dumps(
                {
                    "access_token": token_info["access_token"],
                    "refresh_token": token_info["refresh_token"],
                    "expires_at": token_info["expires_at"],
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                }
            ),
        )
        log.info("Spotify OAuth completed")

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.spotify.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
