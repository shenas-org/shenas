"""Shared Google OAuth2 auth for all Google API sources (Gmail, Calendar, etc.).

Uses the server-side redirect flow: the browser navigates to Google's
consent screen, and Google redirects back to the shenas app's
``/api/auth/source/{name}/callback`` endpoint with an authorization code.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any, ClassVar

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

    from app.table import SingletonTable

log = logging.getLogger(__name__)

# Pending OAuth flows keyed by source name.
# Stores the Flow object so complete_oauth can exchange the code.
_pending_flows: dict[str, Any] = {}

# Shared OAuth client (Desktop app -- safe to embed)
DEFAULT_CLIENT_ID = "232211553387-3c4sog0fokns7ri2o6oj8d3s5v3r9jh6.apps.googleusercontent.com"
DEFAULT_CLIENT_SECRET = "REDACTED_GOOGLE_OAUTH_CLIENT_SECRET"


class GoogleAuth:
    """Reusable Google OAuth2 auth handler with server-side redirect.

    Each source creates an instance with its own scopes and API details.
    """

    AUTH_FIELDS: ClassVar[list[dict[str, str]]] = []
    AUTH_INSTRUCTIONS: str = "Click Authenticate to sign in with your Google account."

    def __init__(
        self,
        name: str,
        scopes: list[str],
        api_name: str,
        api_version: str,
        *,
        auth_cls: type[SingletonTable],
        static_discovery: bool = True,
    ) -> None:
        self.name: str = name
        self.scopes: list[str] = scopes
        self.api_name: str = api_name
        self.api_version: str = api_version
        self.static_discovery: bool = static_discovery
        self.auth_cls: type[SingletonTable] = auth_cls

    def _get_client_config(self) -> dict[str, Any]:
        env_prefix = f"SHENAS_{self.name.upper()}"
        client_id = os.environ.get(f"{env_prefix}_CLIENT_ID", DEFAULT_CLIENT_ID)
        client_secret = os.environ.get(f"{env_prefix}_CLIENT_SECRET", DEFAULT_CLIENT_SECRET)
        return {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

    def _get_stored_token(self) -> Credentials | None:
        row = self.auth_cls.read_row()
        if row and row.get("token"):
            return Credentials.from_authorized_user_info(json.loads(row["token"]), self.scopes)
        return None

    def _store_token(self, creds: Credentials) -> None:
        self.auth_cls.write_row(token=creds.to_json())

    def build_client(self) -> Resource:
        """Build a Google API service from stored tokens."""
        from googleapiclient.discovery import build

        creds = self._get_stored_token()

        if creds and creds.valid:
            return build(self.api_name, self.api_version, credentials=creds, static_discovery=self.static_discovery)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._store_token(creds)
            return build(self.api_name, self.api_version, credentials=creds, static_discovery=self.static_discovery)

        msg = "No valid credentials. Configure authentication in the Auth tab."
        raise RuntimeError(msg)

    # -- Server-side OAuth redirect flow --

    def start_oauth(self, redirect_uri: str) -> str:
        """Generate the Google OAuth authorization URL."""
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(self._get_client_config(), scopes=self.scopes)
        flow.redirect_uri = redirect_uri
        auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")
        _pending_flows[self.name] = {"flow": flow, "state": state}
        log.info("OAuth started for %s, state=%s", self.name, state)
        return auth_url

    def complete_oauth(self, code: str, state: str | None = None) -> None:
        """Exchange the authorization code for tokens and store them."""
        entry = _pending_flows.pop(self.name, None)
        if not entry:
            msg = f"No pending OAuth flow for {self.name}. Start auth again."
            raise RuntimeError(msg)
        if state and entry.get("state") != state:
            msg = "OAuth state mismatch -- possible CSRF"
            raise RuntimeError(msg)
        flow = entry["flow"]
        flow.fetch_token(code=code)
        self._store_token(flow.credentials)
        log.info("OAuth completed for %s", self.name)
