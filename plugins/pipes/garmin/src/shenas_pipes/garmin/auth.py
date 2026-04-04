"""Garmin Connect OAuth token management via encrypted DuckDB."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, ClassVar

from garminconnect import Garmin

from shenas_pipes.core.store import DataclassStore
from shenas_pipes.core.base_auth import PipeAuth
from shenas_schemas.core.field import Field

_auth = DataclassStore("auth")

# Pending MFA state for multi-step auth flow
pending_mfa: dict[str, object] = {}

AUTH_FIELDS: list[dict[str, str | bool]] = [
    {"name": "email", "prompt": "Email", "hide": False},
    {"name": "password", "prompt": "Password", "hide": True},
]


@dataclass
class GarminAuth(PipeAuth):
    """Garmin authentication credentials."""

    __table__: ClassVar[str] = "pipe_garmin"

    tokens: Annotated[
        str | None, Field(db_type="VARCHAR", description="JSON blob of garth token files", category="secret")
    ] = None


def _get_stored_tokens() -> dict[str, Any] | None:
    """Read serialized garth tokens from encrypted DuckDB."""
    row = _auth.get(GarminAuth)
    if row and row.get("tokens"):
        return json.loads(row["tokens"])
    return None


def _store_tokens(token_dir: Path) -> None:
    """Serialize garth token files from a directory into encrypted DuckDB."""
    tokens: dict[str, str] = {}
    for f in token_dir.iterdir():
        if f.suffix == ".json":
            tokens[f.name] = f.read_text()
    _auth.set(GarminAuth, tokens=json.dumps(tokens))


def _tokens_to_dir(tokens: dict[str, str]) -> Path:
    """Write serialized tokens to a temp directory for garth to load."""
    tmp = Path(tempfile.mkdtemp(prefix="garmin_tokens_"))
    for name, content in tokens.items():
        (tmp / name).write_text(content)
    return tmp


def build_client(email: str | None = None, password: str | None = None, **_kwargs: str) -> Garmin:
    """Build a Garmin client from stored tokens or credentials."""
    # Try stored tokens first
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
        raise RuntimeError("No valid tokens found. Configure authentication in the Auth tab.")

    client = Garmin(email=email, password=password)
    with tempfile.TemporaryDirectory(prefix="garmin_tokens_") as tmp:
        try:
            client.login(tmp)
        except Exception:
            client.login()
            client.client.dump(tmp)
        _store_tokens(Path(tmp))

    return client


def save_tokens_from_client(client: Garmin) -> None:
    """Save a client's garth tokens to encrypted DuckDB."""
    with tempfile.TemporaryDirectory(prefix="garmin_tokens_") as tmp:
        client.client.dump(tmp)
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

    result1, result2 = client.login()

    if result1 == "needs_mfa":
        pending_mfa["garmin"] = {"client": client, "mfa_state": result2}
        raise ValueError("MFA code required")

    save_tokens_from_client(client)


def complete_mfa(state: dict[str, Any], mfa_code: str) -> None:
    """Complete a pending MFA login with the provided code."""
    client = state["client"]
    mfa_state = state["mfa_state"]
    client.resume_login(mfa_state, mfa_code)
    save_tokens_from_client(client)
