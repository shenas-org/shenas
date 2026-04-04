"""Duolingo JWT token management via encrypted DuckDB.

Duolingo has no official API and blocks programmatic login with CAPTCHA.
Authentication requires a JWT token extracted from the browser:

1. Log into duolingo.com
2. Open DevTools console (F12)
3. Run: document.cookie.match(new RegExp('(^| )jwt_token=([^;]+)'))[0].slice(11)
4. Paste the token when prompted
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.base_auth import PipeAuth
from shenas_pipes.core.store import DataclassStore
from shenas_pipes.duolingo.client import DuolingoClient
from shenas_schemas.core.field import Field

_auth = DataclassStore("auth")

AUTH_FIELDS: list[dict[str, str | bool]] = [
    {"name": "jwt_token", "prompt": "JWT token", "hide": False},
]

AUTH_INSTRUCTIONS = (
    "Duolingo blocks programmatic login. Extract a JWT from your browser:\n"
    "\n"
    "  1. Log into duolingo.com\n"
    "  2. Open DevTools (F12) > Console\n"
    "  3. Run:  document.cookie.match(/jwt_token=([^;]+)/)[1]\n"
    "  4. Paste the token below"
)


@dataclass
class DuolingoAuth(PipeAuth):
    """Duolingo authentication credentials."""

    __table__: ClassVar[str] = "pipe_duolingo"

    jwt_token: Annotated[str | None, Field(db_type="VARCHAR", description="Browser JWT token", category="secret")] = None


def _get_stored_jwt() -> str | None:
    """Read JWT from encrypted DuckDB."""
    row = _auth.get(DuolingoAuth)
    if row and row.get("jwt_token"):
        return row["jwt_token"]
    return None


def _store_jwt(jwt: str) -> None:
    """Write JWT to encrypted DuckDB."""
    _auth.set(DuolingoAuth, jwt_token=jwt)


def build_client() -> DuolingoClient:
    """Build a Duolingo client from a stored JWT token."""
    jwt = _get_stored_jwt()
    if not jwt:
        raise RuntimeError("No JWT token found. Configure authentication in the Auth tab.")
    return DuolingoClient(jwt)


def authenticate(credentials: dict[str, str]) -> None:
    """Store a Duolingo JWT token extracted from the browser.

    Expected keys: jwt_token.
    """
    jwt = (credentials.get("jwt_token") or "").strip()
    if not jwt:
        raise ValueError("jwt_token is required")

    # Verify the token works
    client = DuolingoClient(jwt)
    try:
        client.get_user()
    finally:
        client.close()
    _store_jwt(jwt)
