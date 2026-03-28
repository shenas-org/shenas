"""Gmail OAuth2 token management via OS keyring."""

import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "gmail_token"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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


def build_client(client_secrets_path: str | None = None):  # type: ignore[no-untyped-def]
    """Build a Gmail API service from keyring tokens or OAuth flow."""
    creds = _get_stored_token()

    if creds and creds.valid:
        return build("gmail", "v1", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _store_token(creds)
        return build("gmail", "v1", credentials=creds)

    if client_secrets_path:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
        creds = flow.run_local_server(port=0)
        _store_token(creds)
        return build("gmail", "v1", credentials=creds)

    raise RuntimeError("No valid Gmail credentials. Run 'shenas pipe gmail auth' first.")
