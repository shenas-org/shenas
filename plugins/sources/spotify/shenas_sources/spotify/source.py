"""Spotify source -- syncs listening data via OAuth2 PKCE."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from spotipy.cache_handler import CacheHandler

from app.table import Field
from shenas_sources.core.access_type import OFFICIAL_API
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source

REDIRECT_URI = "http://127.0.0.1:8090/callback"
SCOPES = "user-read-recently-played user-top-read user-library-read user-follow-read playlist-read-private user-read-email"
DEFAULT_CLIENT_ID = "07f7c412747c406ca429189cb724ec36"

# Module-level storage for the PKCE manager between start_oauth and complete_oauth
_pending_pkce: dict[str, Any] = {}


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
    entity_types: ClassVar[list[str]] = ["human"]
    description = (
        "Syncs listening data from Spotify.\n\n"
        "Uses OAuth2 PKCE flow. Click Authenticate to sign in with your "
        "Spotify account.\n\n"
        "Poll frequently (~1-2 hours) to build complete listening history."
    )
    access_types = (OFFICIAL_API,)

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

    auth_instructions = "Click Authenticate to sign in with your Spotify account."

    @property
    def auth_fields(self) -> list:  # No user input -- uses hardcoded client ID
        return []

    @property
    def supports_oauth_redirect(self) -> bool:
        return True

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:  # noqa: ARG002
        """Start the Spotify PKCE OAuth flow and return the authorization URL."""
        from spotipy.oauth2 import SpotifyPKCE

        client_id = os.environ.get("SPOTIFY_CLIENT_ID", DEFAULT_CLIENT_ID)

        cache = _MemoryCacheHandler()
        pkce = SpotifyPKCE(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=SCOPES,
            open_browser=False,
            cache_handler=cache,
        )

        auth_url = pkce.get_authorize_url()
        _pending_pkce["spotify"] = {
            "pkce": pkce,
            "cache": cache,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        }
        return auth_url

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:  # noqa: ARG002
        """Complete the Spotify PKCE flow with the authorization code."""
        pending = _pending_pkce.pop("spotify", None)
        if not pending:
            msg = "No pending Spotify auth flow. Start authentication again."
            raise RuntimeError(msg)

        pkce = pending["pkce"]
        cache = pending["cache"]
        client_id = pending["client_id"]

        pkce.get_access_token(code, check_cache=False)
        token_info = cache.token_info
        if not token_info:
            msg = "Token exchange failed -- no token received from Spotify"
            raise RuntimeError(msg)

        self.Auth.write_row(
            tokens=json.dumps(
                {
                    "access_token": token_info["access_token"],
                    "refresh_token": token_info["refresh_token"],
                    "expires_at": token_info["expires_at"],
                    "client_id": client_id,
                }
            ),
        )

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

        redirect_uri = tokens.get("redirect_uri", "http://127.0.0.1:7280/api/auth/source/spotify/callback")
        client_id = tokens.get("client_id") or os.environ.get("SPOTIFY_CLIENT_ID", DEFAULT_CLIENT_ID)
        pkce = SpotifyPKCE(
            client_id=client_id,
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

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.spotify.tables import TABLES, reset_track_id_cache

        reset_track_id_cache()
        return [t.to_resource(client) for t in TABLES]
