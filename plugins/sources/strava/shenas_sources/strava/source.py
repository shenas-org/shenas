"""Strava source -- syncs activities and athlete profile via OAuth2."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Annotated, Any, cast

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source

log = logging.getLogger(__name__)

SCOPES = ["read", "activity:read_all", "profile:read_all"]

# Pending OAuth state for the redirect flow
_pending_oauth: dict[str, dict[str, Any]] = {}


class StravaSource(Source):
    name = "strava"
    display_name = "Strava"
    primary_table = "activities"
    description = (
        "Syncs activities (with laps, kudos, comments), athlete profile, "
        "athlete totals, heart rate / power zones, and gear from Strava."
    )

    @dataclass
    class Auth(SourceAuth):
        tokens: (
            Annotated[
                str | None,
                Field(
                    db_type="VARCHAR",
                    description="JSON blob of OAuth2 tokens (access, refresh, client_id, client_secret)",
                    category="secret",
                ),
            ]
            | None
        ) = None

    auth_instructions = (
        "Strava requires a user-owned API application for OAuth2 access.\n"
        "\n"
        "  1. Go to https://www.strava.com/settings/api\n"
        "  2. Create an app (any name/website is fine)\n"
        "  3. Set Authorization Callback Domain to match your shenas host\n"
        "     (e.g. 127.0.0.1 for local development)\n"
        "  4. Enter the Client ID and Client Secret below"
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "client_id", "prompt": "Client ID (numeric, from strava.com/settings/api)", "hide": False},
            {"name": "client_secret", "prompt": "Client Secret", "hide": True},
        ]

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
            refreshed = cast(
                "dict[str, Any]",
                client.refresh_access_token(
                    client_id=int(tokens["client_id"]),
                    client_secret=tokens["client_secret"],
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

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:
        from stravalib.client import Client

        creds = credentials or {}
        client_id = creds.get("client_id", "").strip()
        client_secret = creds.get("client_secret", "").strip()
        if not client_id or not client_secret:
            msg = "client_id and client_secret are required"
            raise ValueError(msg)
        if not client_id.isdigit():
            msg = "Client ID must be a number (find it at strava.com/settings/api)"
            raise ValueError(msg)

        client = Client()
        auth_url = client.authorization_url(
            client_id=int(client_id),
            redirect_uri=redirect_uri,
            scope=SCOPES,  # ty: ignore[invalid-argument-type]
        )

        _pending_oauth[self.name] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }
        log.info("Strava OAuth started, redirect_uri=%s", redirect_uri)
        return auth_url

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:  # noqa: ARG002
        from stravalib.client import Client

        entry = _pending_oauth.pop(self.name, None)
        if not entry:
            msg = "No pending Strava OAuth flow. Start auth again."
            raise RuntimeError(msg)

        client_id = entry["client_id"]
        client_secret = entry["client_secret"]

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
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )
        log.info("Strava OAuth completed")

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.strava.tables import TABLES, fetch_detailed_activities

        # Fetch detailed activities once and share via the `detailed` context
        # kwarg with Activities / Laps / Kudos / Comments so we don't call
        # get_activity() / get_activity_kudos() / etc. more than necessary.
        # Tables that don't need it (Athlete, AthleteStats, AthleteZones, Gear)
        # just ignore the extra kwarg.
        detailed = fetch_detailed_activities(client)
        return [t.to_resource(client, detailed=detailed) for t in TABLES]
