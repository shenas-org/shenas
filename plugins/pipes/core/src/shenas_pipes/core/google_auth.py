"""Shared Google OAuth2 auth for all Google API pipes (Gmail, Calendar, Photos, etc.)."""

from __future__ import annotations

import io
import json
import os
import sys
import threading
import time
from typing import TYPE_CHECKING, Any, ClassVar

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

# Shared state for multi-step OAuth flows (e.g. URL passback).
# Keys are pipe names, values are dicts with thread + state.
pending_oauth: dict[str, dict[str, Any]] = {}

# Shared OAuth client (Desktop app -- safe to embed)
DEFAULT_CLIENT_ID = "232211553387-3c4sog0fokns7ri2o6oj8d3s5v3r9jh6.apps.googleusercontent.com"
DEFAULT_CLIENT_SECRET = "REDACTED_GOOGLE_OAUTH_CLIENT_SECRET"


class GoogleAuth:
    """Reusable Google OAuth2 auth handler.

    Each pipe creates an instance with its own name, scopes, and API details.
    Token storage, OAuth flow, and REST auth passback are all handled here.
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
        auth_cls: type,
        static_discovery: bool = True,
    ) -> None:
        self.name: str = name
        self.scopes: list[str] = scopes
        self.api_name: str = api_name
        self.api_version: str = api_version
        self.static_discovery: bool = static_discovery
        self.auth_cls: type = auth_cls

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
        from shenas_pipes.core.store import DataclassStore

        _auth = DataclassStore("auth")
        row = _auth.get(self.auth_cls)
        if row and row.get("token"):
            return Credentials.from_authorized_user_info(json.loads(row["token"]), self.scopes)
        return None

    def _store_token(self, creds: Credentials) -> None:
        self._store_token_str(creds.to_json())

    def _store_token_str(self, token_json: str) -> None:
        from shenas_pipes.core.store import DataclassStore

        _auth = DataclassStore("auth")
        _auth.set(self.auth_cls, token=token_json)

    def build_client(self, run_auth_flow: bool = False) -> Resource:
        """Build a Google API service from stored tokens or OAuth flow."""
        creds = self._get_stored_token()

        if creds and creds.valid:
            return build(self.api_name, self.api_version, credentials=creds, static_discovery=self.static_discovery)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._store_token(creds)
            return build(self.api_name, self.api_version, credentials=creds, static_discovery=self.static_discovery)

        if run_auth_flow:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_config(self._get_client_config(), self.scopes)
            creds = flow.run_local_server(port=0)
            self._store_token(creds)
            return build(self.api_name, self.api_version, credentials=creds, static_discovery=self.static_discovery)

        raise RuntimeError("No valid credentials. Configure authentication in the Auth tab.")

    def authenticate(self, credentials: dict[str, str]) -> None:
        """OAuth2 browser flow with URL passback for the REST auth API."""
        from google_auth_oauthlib.flow import InstalledAppFlow

        from shenas_pipes.core.google_auth import pending_oauth

        if credentials.get("auth_complete") == "true" and self.name in pending_oauth:
            state = pending_oauth.pop(self.name)
            thread = state["thread"]
            thread.join(timeout=120)
            if thread.is_alive():
                raise RuntimeError("OAuth flow timed out.")
            if state.get("error"):
                raise RuntimeError(state["error"])
            return

        flow = InstalledAppFlow.from_client_config(self._get_client_config(), self.scopes)
        state: dict[str, Any] = {"url": None}
        store_token = self._store_token

        class _UrlCapture(io.TextIOBase):
            def __init__(self, original: io.TextIOBase) -> None:
                self._original = original

            def write(self, s: str) -> int:
                if "accounts.google.com" in s:
                    for part in s.split():
                        if part.startswith("https://accounts.google.com"):
                            state["url"] = part.strip()
                            break
                return self._original.write(s)

            def flush(self) -> None:
                self._original.flush()

        def _run_flow() -> None:
            old_stdout = sys.stdout
            sys.stdout = _UrlCapture(old_stdout)
            try:
                creds = flow.run_local_server(port=0, open_browser=False)
                store_token(creds)
            except Exception as exc:
                state["error"] = str(exc)
            finally:
                sys.stdout = old_stdout

        thread = threading.Thread(target=_run_flow, daemon=True)
        thread.start()

        for _ in range(50):
            if state.get("url"):
                break
            time.sleep(0.1)

        state["thread"] = thread
        pending_oauth[self.name] = state

        auth_url = state.get("url", "")
        if not auth_url:
            raise RuntimeError("Failed to get OAuth URL.")
        raise ValueError(f"OAUTH_URL:{auth_url}")
