"""Lunch Money API key management via encrypted DuckDB."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from lunchable import LunchMoney

from shenas_pipes.core.store import DataclassStore
from shenas_pipes.core.base_auth import PipeAuth
from shenas_schemas.core.field import Field

_auth = DataclassStore("auth")

AUTH_FIELDS: list[dict[str, str | bool]] = [
    {"name": "api_key", "prompt": "API key", "hide": True},
]


@dataclass
class LunchMoneyAuth(PipeAuth):
    """Lunch Money authentication credentials."""

    __table__: ClassVar[str] = "pipe_lunchmoney"

    api_key: Annotated[str | None, Field(db_type="VARCHAR", description="Lunch Money API key", category="secret")] = None


def _get_stored_key() -> str | None:
    """Read API key from encrypted DuckDB."""
    row = _auth.get(LunchMoneyAuth)
    if row and row.get("api_key"):
        return row["api_key"]
    return None


def _store_key(api_key: str) -> None:
    """Write API key to encrypted DuckDB."""
    _auth.set(LunchMoneyAuth, api_key=api_key)


def build_client(api_key: str | None = None, **_kwargs: str) -> LunchMoney:
    """Build a Lunch Money client from provided key or stored credentials."""
    if api_key:
        _store_key(api_key)
        return LunchMoney(access_token=api_key)

    stored = _get_stored_key()
    if stored:
        return LunchMoney(access_token=stored)

    raise RuntimeError("No API key found. Configure authentication in the Auth tab.")


def authenticate(credentials: dict[str, str]) -> None:
    """Authenticate with Lunch Money using an API key.

    Expected keys: api_key (or password as alias).
    """
    api_key = credentials.get("api_key") or credentials.get("password")
    if not api_key:
        raise ValueError("api_key is required")

    client = build_client(api_key=api_key)
    client.get_user()  # verify the key works
