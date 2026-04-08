"""Strava source -- syncs activities and athlete profile via OAuth2."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Annotated, Any, cast

from shenas_plugins.core.base_auth import SourceAuth
from shenas_plugins.core.field import Field
from shenas_sources.core.source import Source

REDIRECT_URI = "http://127.0.0.1:8091/callback"
SCOPES = ["read", "activity:read_all", "profile:read_all"]

_pending_auth: dict[str, Any] = {}


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
        "  3. Set Authorization Callback Domain to: 127.0.0.1\n"
        "  4. Enter the Client ID and Client Secret below"
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "client_id", "prompt": "Client ID", "hide": False},
            {"name": "client_secret", "prompt": "Client Secret", "hide": True},
        ]

    def _load_tokens(self) -> dict[str, Any]:
        row = self._auth_store.get(self.Auth)
        if not row or not row.get("tokens"):
            msg = "No Strava tokens found. Configure authentication in the Auth tab."
            raise RuntimeError(msg)
        return json.loads(row["tokens"])

    def _save_tokens(self, tokens: dict[str, Any]) -> None:
        self._auth_store.set(self.Auth, tokens=json.dumps(tokens))

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

    def authenticate(self, credentials: dict[str, str]) -> None:
        if credentials.get("auth_complete") == "true":
            state = _pending_auth.pop("strava", None)
            if state is None:
                msg = "No pending auth flow. Start auth again."
                raise ValueError(msg)
            state["thread"].join(timeout=120)
            if state.get("error"):
                raise RuntimeError(state["error"])
            return

        client_id = (credentials.get("client_id") or "").strip()
        client_secret = (credentials.get("client_secret") or "").strip()
        if not client_id or not client_secret:
            msg = "client_id and client_secret are required"
            raise ValueError(msg)

        from stravalib.client import Client

        client = Client()
        auth_url = client.authorization_url(
            client_id=int(client_id),
            redirect_uri=REDIRECT_URI,
            scope=SCOPES,
        )

        state: dict[str, Any] = {}
        save_tokens = self._save_tokens

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

                def log_message(self, fmt: str, *args: Any) -> None:
                    pass

            try:
                server = HTTPServer(("127.0.0.1", 8091), Handler)
                server.timeout = 120
                server.handle_request()
                server.server_close()

                if "error" in code_result:
                    state["error"] = f"Authorization denied: {code_result['error']}"
                    return
                if "code" not in code_result:
                    state["error"] = "Authorization timed out"
                    return

                token_response = cast(
                    "dict[str, Any]",
                    client.exchange_code_for_token(
                        client_id=int(client_id),
                        client_secret=client_secret,
                        code=code_result["code"],
                    ),
                )
                save_tokens(
                    {
                        "access_token": token_response["access_token"],
                        "refresh_token": token_response["refresh_token"],
                        "expires_at": token_response["expires_at"],
                        "client_id": client_id,
                        "client_secret": client_secret,
                    }
                )
            except Exception as exc:
                state["error"] = str(exc)

        thread = threading.Thread(target=_run_flow, daemon=True)
        thread.start()
        state["thread"] = thread
        _pending_auth["strava"] = state

        msg = f"OAUTH_URL:{auth_url}"
        raise ValueError(msg)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.strava.resources import (
            activities,
            athlete,
            athlete_stats,
            athlete_zones,
            comments,
            fetch_detailed_activities,
            gear,
            kudos,
            laps,
        )

        # Fetch detailed activities once and share across activities/laps/kudos/comments
        # so we don't call get_activity() / get_activity_kudos() / etc. more than necessary.
        detailed = fetch_detailed_activities(client)

        return [
            activities(detailed),
            laps(detailed),
            kudos(client, detailed),
            comments(client, detailed),
            athlete(client),
            athlete_stats(client),
            athlete_zones(client),
            gear(client),
        ]
