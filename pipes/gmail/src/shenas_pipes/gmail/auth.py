"""Gmail OAuth2 token management via OS keyring."""

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "gmail_token"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

GMAIL_CLIENT_ID = "232211553387-3c4sog0fokns7ri2o6oj8d3s5v3r9jh6.apps.googleusercontent.com"
GMAIL_CLIENT_SECRET = "REDACTED_GOOGLE_OAUTH_CLIENT_SECRET"


def _get_client_config() -> dict:
    """Build the OAuth client config from embedded or env var credentials."""
    client_id = os.environ.get("SHENAS_GMAIL_CLIENT_ID", GMAIL_CLIENT_ID)
    client_secret = os.environ.get("SHENAS_GMAIL_CLIENT_SECRET", GMAIL_CLIENT_SECRET)
    if not client_id or not client_secret:
        raise RuntimeError(
            "Gmail OAuth credentials not configured. Either:\n"
            "  1. Set SHENAS_GMAIL_CLIENT_ID and SHENAS_GMAIL_CLIENT_SECRET env vars, or\n"
            "  2. Embed them in pipes/gmail/src/shenas_pipes/gmail/auth.py"
        )
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def _get_stored_token() -> Credentials | None:
    """Read OAuth2 credentials from OS keyring."""
    try:
        import keyring

        data = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if data:
            return Credentials.from_authorized_user_info(json.loads(data), SCOPES)
    except Exception:
        pass
    return None


def _store_token(creds: Credentials) -> None:
    """Write OAuth2 credentials to OS keyring."""
    import keyring

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        pass
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, creds.to_json())


def build_client(run_auth_flow: bool = False):  # type: ignore[no-untyped-def]
    """Build a Gmail API service from keyring tokens or OAuth flow."""
    creds = _get_stored_token()

    if creds and creds.valid:
        return build("gmail", "v1", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _store_token(creds)
        return build("gmail", "v1", credentials=creds)

    if run_auth_flow:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_config(_get_client_config(), SCOPES)
        creds = flow.run_local_server(port=0)
        _store_token(creds)
        return build("gmail", "v1", credentials=creds)

    raise RuntimeError("No valid Gmail credentials. Run 'shenasctl pipe gmail auth' first.")


def authenticate(credentials: dict[str, str]) -> None:
    """Authenticate with Gmail via OAuth2 browser flow.

    No credentials needed -- opens a browser for Google login.
    """
    build_client(run_auth_flow=True)
