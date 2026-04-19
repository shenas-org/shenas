"""Strava source -- syncs activities and athlete profile via OAuth2."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Annotated, Any, cast

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source

SCOPES = ["read", "activity:read_all", "profile:read_all"]

# Shared OAuth client credentials (safe to embed -- see Google's guidance on
# "installed app" secrets: they identify the app, not the user).
DEFAULT_CLIENT_ID = "221841"
DEFAULT_CLIENT_SECRET = "b82349804786a7e5648935945556f97ab6845186"

# Pending OAuth state for the redirect flow
_pending_oauth: dict[str, dict[str, Any]] = {}


def _get_credentials() -> tuple[str, str]:
    """Return (client_id, client_secret) with env-var override support."""
    client_id = os.environ.get("SHENAS_STRAVA_CLIENT_ID", DEFAULT_CLIENT_ID)
    client_secret = os.environ.get("SHENAS_STRAVA_CLIENT_SECRET", DEFAULT_CLIENT_SECRET)
    return client_id, client_secret


class StravaSource(Source):
    name = "strava"
    display_name = "Strava"
    primary_table = "activities"
    description = (
        "Syncs activities (with laps, kudos, comments), athlete profile, "
        "athlete totals, heart rate / power zones, and gear from Strava."
    )

    @dataclass
    class Config(SourceConfig):
        lookback_period: Annotated[
            int | None,
            Field(
                db_type="INTEGER",
                description="How many days back to fetch on initial sync (unset = source default)",
                ui_widget="text",
                example_value="30",
            ),
        ] = None

    @dataclass
    class Auth(SourceAuth):
        tokens: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description="JSON blob of OAuth2 tokens (access, refresh)",
                    category="secret",
                ),
            ]
            | None
        ) = None

    auth_instructions = "Click Authenticate to sign in with your Strava account."

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return []

    def _load_tokens(self) -> dict[str, Any]:
        row = self.Auth.read_row()
        if not row or not row.get("tokens"):
            msg = "No Strava tokens found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return json.loads(row["tokens"])

    def _save_tokens(self, tokens: dict[str, Any]) -> None:
        self.Auth.write_row(tokens=json.dumps(tokens))

    def build_client(self) -> Any:
        from stravalib.client import Client

        tokens = self._load_tokens()
        client = Client(access_token=tokens["access_token"])

        # Refresh if expired (or about to)
        if tokens.get("expires_at", 0) - time.time() < 60:
            client_id, client_secret = _get_credentials()
            refreshed = cast(
                "dict[str, Any]",
                client.refresh_access_token(
                    client_id=int(client_id),
                    client_secret=client_secret,
                    refresh_token=tokens["refresh_token"],
                ),
            )
            tokens["access_token"] = refreshed["access_token"]
            tokens["refresh_token"] = refreshed["refresh_token"]
            tokens["expires_at"] = refreshed["expires_at"]
            self._save_tokens(tokens)
            client = Client(access_token=tokens["access_token"])

        return client

    # -- OAuth redirect flow --

    @property
    def supports_oauth_redirect(self) -> bool:
        return True

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:  # noqa: ARG002
        from stravalib.client import Client

        client_id, _ = _get_credentials()

        client = Client()
        auth_url = client.authorization_url(
            client_id=int(client_id),
            redirect_uri=redirect_uri,
            scope=SCOPES,  # ty: ignore[invalid-argument-type]
        )

        _pending_oauth[self.name] = {"redirect_uri": redirect_uri}
        self.log.info("Strava OAuth started, redirect_uri=%s", redirect_uri)
        return auth_url

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:  # noqa: ARG002
        from stravalib.client import Client

        entry = _pending_oauth.pop(self.name, None)
        if not entry:
            msg = "No pending Strava OAuth flow. Start auth again."
            raise RuntimeError(msg)

        client_id, client_secret = _get_credentials()

        client = Client()
        token_response = cast(
            "dict[str, Any]",
            client.exchange_code_for_token(
                client_id=int(client_id),
                client_secret=client_secret,
                code=code,
            ),
        )
        self._save_tokens(
            {
                "access_token": token_response["access_token"],
                "refresh_token": token_response["refresh_token"],
                "expires_at": token_response["expires_at"],
            }
        )
        self.log.info("Strava OAuth completed")

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.strava.tables import TABLES, fetch_detailed_activities

        # Fetch detailed activities once and share via the `detailed` context
        # kwarg with Activities / Laps / Kudos / Comments so we don't call
        # get_activity() / get_activity_kudos() / etc. more than necessary.
        # Tables that don't need it (Athlete, AthleteStats, AthleteZones, Gear)
        # just ignore the extra kwarg.
        start = self._lookback_start_date(30)
        detailed = fetch_detailed_activities(client, start_date=start)
        return [t.to_resource(client, detailed=detailed) for t in TABLES]
