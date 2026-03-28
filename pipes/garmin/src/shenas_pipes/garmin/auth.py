"""Garmin Connect OAuth token management via OS keyring."""

import json
import tempfile
from pathlib import Path

from garminconnect import Garmin

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "garmin_tokens"

# Pending MFA state for multi-step auth flow
pending_mfa: dict[str, object] = {}

AUTH_FIELDS = [
    {"name": "email", "prompt": "Email", "hide": False},
    {"name": "password", "prompt": "Password", "hide": True},
]


def _get_stored_tokens() -> dict | None:
    """Read serialized garth tokens from OS keyring."""
    try:
        import keyring

        data = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def _store_tokens(token_dir: Path) -> None:
    """Serialize garth token files from a directory into OS keyring."""
    import keyring

    tokens = {}
    for f in token_dir.iterdir():
        if f.suffix == ".json":
            tokens[f.name] = f.read_text()
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        pass
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, json.dumps(tokens))


def _tokens_to_dir(tokens: dict) -> Path:
    """Write serialized tokens to a temp directory for garth to load."""
    tmp = Path(tempfile.mkdtemp(prefix="garmin_tokens_"))
    for name, content in tokens.items():
        (tmp / name).write_text(content)
    return tmp


def build_client(email: str | None = None, password: str | None = None, **_kwargs: str) -> Garmin:
    """Build a Garmin client from keyring tokens or credentials."""
    # Try keyring tokens first
    stored = _get_stored_tokens()
    if stored:
        tmp_dir = _tokens_to_dir(stored)
        client = Garmin()
        try:
            client.login(str(tmp_dir))
            return client
        except Exception:
            pass

    # Fall back to credential login
    if not email or not password:
        raise RuntimeError("No valid tokens found. Run 'shenas pipe garmin auth' first.")

    client = Garmin(email=email, password=password)
    with tempfile.TemporaryDirectory(prefix="garmin_tokens_") as tmp:
        try:
            client.login(tmp)
        except Exception:
            client.login()
            client.garth.dump(tmp)
        _store_tokens(Path(tmp))

    return client


def save_tokens_from_client(client: Garmin) -> None:
    """Save a client's garth tokens to OS keyring."""
    with tempfile.TemporaryDirectory(prefix="garmin_tokens_") as tmp:
        client.garth.dump(tmp)
        _store_tokens(Path(tmp))


BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def authenticate(credentials: dict[str, str]) -> None:
    """Authenticate with Garmin Connect using provided credentials.

    Expected keys: email, password.
    Raises ValueError("MFA code required") if MFA is needed -- the caller
    should store the pending state and call complete_mfa() with the code.
    """
    email = credentials.get("email")
    password = credentials.get("password")

    if not email or not password:
        raise ValueError("email and password are required")

    client = Garmin(email=email, password=password, return_on_mfa=True)
    client.garth.sess.headers.update({"User-Agent": BROWSER_UA})
    client.garth.oauth1_token = None
    client.garth.oauth2_token = None

    result1, result2 = client.login()

    if result1 == "needs_mfa":
        pending_mfa["garmin"] = {"client": client, "mfa_state": result2}
        raise ValueError("MFA code required")

    save_tokens_from_client(client)


def complete_mfa(state: object, mfa_code: str) -> None:
    """Complete a pending MFA login with the provided code."""
    client = state["client"]
    mfa_state = state["mfa_state"]
    client.resume_login(mfa_state, mfa_code)
    save_tokens_from_client(client)
