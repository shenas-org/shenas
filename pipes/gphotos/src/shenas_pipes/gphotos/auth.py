"""Google Photos OAuth2 token management via OS keyring."""

import io
import json
import os
import sys
import threading
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "gphotos_token"
SCOPES = ["https://www.googleapis.com/auth/photoslibrary.readonly"]

GPHOTOS_CLIENT_ID = "232211553387-3c4sog0fokns7ri2o6oj8d3s5v3r9jh6.apps.googleusercontent.com"
GPHOTOS_CLIENT_SECRET = "REDACTED_GOOGLE_OAUTH_CLIENT_SECRET"

AUTH_FIELDS = []


def _get_client_config() -> dict:
    client_id = os.environ.get("SHENAS_GPHOTOS_CLIENT_ID", GPHOTOS_CLIENT_ID)
    client_secret = os.environ.get("SHENAS_GPHOTOS_CLIENT_SECRET", GPHOTOS_CLIENT_SECRET)
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
    try:
        import keyring

        data = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if data:
            return Credentials.from_authorized_user_info(json.loads(data), SCOPES)
    except Exception:
        pass
    return None


def _store_token(creds: Credentials) -> None:
    import keyring

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        pass
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, creds.to_json())


def build_client(run_auth_flow: bool = False):  # noqa: ANN201
    """Build a Google Photos API service from keyring tokens or OAuth flow."""
    creds = _get_stored_token()

    if creds and creds.valid:
        return build("photoslibrary", "v1", credentials=creds, static_discovery=False)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _store_token(creds)
        return build("photoslibrary", "v1", credentials=creds, static_discovery=False)

    if run_auth_flow:
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_config(_get_client_config(), SCOPES)
        creds = flow.run_local_server(port=0)
        _store_token(creds)
        return build("photoslibrary", "v1", credentials=creds, static_discovery=False)

    raise RuntimeError("No valid Google Photos credentials. Run 'shenasctl pipe gphotos auth' first.")


def authenticate(credentials: dict[str, str]) -> None:
    """Authenticate with Google Photos via OAuth2."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    from app.api.auth import _pending_mfa

    if credentials.get("auth_complete") == "true" and "gphotos" in _pending_mfa:
        state = _pending_mfa.pop("gphotos")
        thread = state["thread"]
        thread.join(timeout=120)
        if thread.is_alive():
            raise RuntimeError("OAuth flow timed out.")
        if state.get("error"):
            raise RuntimeError(state["error"])
        return

    flow = InstalledAppFlow.from_client_config(_get_client_config(), SCOPES)
    state: dict = {"url": None}

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
            _store_token(creds)
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
    _pending_mfa["gphotos"] = state

    auth_url = state.get("url", "")
    if not auth_url:
        raise RuntimeError("Failed to get OAuth URL.")
    raise ValueError(f"OAUTH_URL:{auth_url}")
