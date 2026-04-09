"""Withings source -- syncs body measurements, sleep, and activity via OAuth2."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Annotated, Any
from urllib.parse import urlencode

from shenas_plugins.core.base_auth import SourceAuth
from shenas_plugins.core.table import Field
from shenas_sources.core.source import Source

REDIRECT_URI = "http://127.0.0.1:8092/callback"
SCOPES = "user.info,user.metrics,user.activity,user.sleepevents"
AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"

_pending_auth: dict[str, Any] = {}


class WithingsSource(Source):
    name = "withings"
    display_name = "Withings"
    primary_table = "measurements"
    description = (
        "Syncs body measurements (weight, body fat, blood pressure, SpO2), "
        "sleep summaries, daily activity, and device info from Withings.\n\n"
        "Requires a Withings developer application for OAuth2 access."
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
        "Withings requires a developer application for OAuth2 access.\n"
        "\n"
        "  1. Go to https://developer.withings.com/dashboard\n"
        "  2. Create an app (any name is fine)\n"
        "  3. Set Callback URL to: http://127.0.0.1:8092/callback\n"
        "  4. Enter the Client ID and Consumer Secret below"
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "client_id", "prompt": "Client ID", "hide": False},
            {"name": "client_secret", "prompt": "Consumer Secret", "hide": True},
        ]

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
            refreshed = WithingsClient.refresh_tokens(
                tokens["client_id"],
                tokens["client_secret"],
                tokens["refresh_token"],
            )
            tokens["access_token"] = refreshed["access_token"]
            tokens["refresh_token"] = refreshed["refresh_token"]
            tokens["expires_at"] = time.time() + refreshed.get("expires_in", 10800)
            self._save_tokens(tokens)

        return WithingsClient(tokens["access_token"])

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.withings.client import WithingsClient

        if credentials.get("auth_complete") == "true":
            state = _pending_auth.pop("withings", None)
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

        auth_url = (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": client_id,
                    "redirect_uri": REDIRECT_URI,
                    "scope": SCOPES,
                    "state": "withings",
                }
            )
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
                server = HTTPServer(("127.0.0.1", 8092), Handler)
                server.timeout = 120
                server.handle_request()
                server.server_close()

                if "error" in code_result:
                    state["error"] = f"Authorization denied: {code_result['error']}"
                    return
                if "code" not in code_result:
                    state["error"] = "Authorization timed out"
                    return

                token_response = WithingsClient.exchange_code(
                    client_id,
                    client_secret,
                    code_result["code"],
                    REDIRECT_URI,
                )
                save_tokens(
                    {
                        "access_token": token_response["access_token"],
                        "refresh_token": token_response["refresh_token"],
                        "expires_at": time.time() + token_response.get("expires_in", 10800),
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "userid": token_response.get("userid"),
                    }
                )
            except Exception as exc:
                state["error"] = str(exc)

        thread = threading.Thread(target=_run_flow, daemon=True)
        thread.start()
        state["thread"] = thread
        _pending_auth["withings"] = state

        msg = f"OAUTH_URL:{auth_url}"
        raise ValueError(msg)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.withings.tables import TABLES

        return [t.to_resource(client, start_date="30 days ago") for t in TABLES]
