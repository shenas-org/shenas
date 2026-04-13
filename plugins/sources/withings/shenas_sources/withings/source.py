"""Withings source -- syncs body measurements, sleep, and activity via OAuth2."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Annotated, Any
from urllib.parse import urlencode

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.source import Source

log = logging.getLogger(__name__)

SCOPES = "user.info,user.metrics,user.activity,user.sleepevents"
AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"

# Shared OAuth client credentials (safe to embed -- see Google's guidance on
# "installed app" secrets: they identify the app, not the user).
DEFAULT_CLIENT_ID = "50f00c6627ece624760c2fc4158848d7e378bcde7be73e4912dc90d4dcc9e866"
DEFAULT_CLIENT_SECRET = "04260e425cd60bc11c4f8755a7e76f0641df62daeec68d28d3ee9b0082bf74dc"

# Pending OAuth state for the redirect flow
_pending_oauth: dict[str, dict[str, Any]] = {}


def _get_credentials() -> tuple[str, str]:
    """Return (client_id, client_secret) with env-var override support."""
    client_id = os.environ.get("SHENAS_WITHINGS_CLIENT_ID", DEFAULT_CLIENT_ID)
    client_secret = os.environ.get("SHENAS_WITHINGS_CLIENT_SECRET", DEFAULT_CLIENT_SECRET)
    return client_id, client_secret


class WithingsSource(Source):
    name = "withings"
    display_name = "Withings"
    primary_table = "measurements"
    description = (
        "Syncs body measurements (weight, body fat, blood pressure, SpO2), "
        "sleep summaries, daily activity, and device info from Withings."
    )

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

    auth_instructions = "Click Authenticate to sign in with your Withings account."

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return []

    def _load_tokens(self) -> dict[str, Any]:
        row = self.Auth.read_row()
        if not row or not row.get("tokens"):
            msg = "No Withings tokens found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return json.loads(row["tokens"])

    def _save_tokens(self, tokens: dict[str, Any]) -> None:
        self.Auth.write_row(tokens=json.dumps(tokens))

    def build_client(self) -> Any:
        from shenas_sources.withings.client import WithingsClient

        tokens = self._load_tokens()

        # Refresh if expired or about to expire
        if tokens.get("expires_at", 0) - time.time() < 60:
            client_id, client_secret = _get_credentials()
            refreshed = WithingsClient.refresh_tokens(
                client_id,
                client_secret,
                tokens["refresh_token"],
            )
            tokens["access_token"] = refreshed["access_token"]
            tokens["refresh_token"] = refreshed["refresh_token"]
            tokens["expires_at"] = time.time() + refreshed.get("expires_in", 10800)
            self._save_tokens(tokens)

        return WithingsClient(tokens["access_token"])

    # -- OAuth redirect flow --

    @property
    def supports_oauth_redirect(self) -> bool:
        return True

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:  # noqa: ARG002
        client_id, _ = _get_credentials()

        auth_url = (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "scope": SCOPES,
                    "state": "withings",
                }
            )
        )

        _pending_oauth[self.name] = {"redirect_uri": redirect_uri}
        log.info("Withings OAuth started, redirect_uri=%s", redirect_uri)
        return auth_url

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:  # noqa: ARG002
        from shenas_sources.withings.client import WithingsClient

        entry = _pending_oauth.pop(self.name, None)
        if not entry:
            msg = "No pending Withings OAuth flow. Start auth again."
            raise RuntimeError(msg)

        client_id, client_secret = _get_credentials()
        redirect_uri = entry["redirect_uri"]

        token_response = WithingsClient.exchange_code(
            client_id,
            client_secret,
            code,
            redirect_uri,
        )
        self._save_tokens(
            {
                "access_token": token_response["access_token"],
                "refresh_token": token_response["refresh_token"],
                "expires_at": time.time() + token_response.get("expires_in", 10800),
                "userid": token_response.get("userid"),
            }
        )
        log.info("Withings OAuth completed")

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.withings.tables import TABLES

        return [t.to_resource(client, start_date="30 days ago") for t in TABLES]
