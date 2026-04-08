"""Active user session persistence (single-row, survives restarts)."""

from __future__ import annotations

import secrets
from typing import Annotated, ClassVar

from shenas_plugins.core.table import Field, Table


class LocalSession(Table):
    """Active local user session.

    Single-row table -- ``id`` is always 1.  The ``token`` is generated
    on login and stored in the browser's ``localStorage``; the backend
    validates it per-request via ``validate_token()``.
    """

    table_name: ClassVar[str] = "local_sessions"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Local Sessions"
    table_description: ClassVar[str | None] = "Active user session (single row, persists across restarts)."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Session ID")] = 1
    user_id: (
        Annotated[int, Field(db_type="INTEGER", description="FK to local_users.id")] | None
    ) = None
    token: Annotated[str, Field(db_type="VARCHAR", description="Random session token")] | None = None
    started_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When session started")] | None
    ) = None
    expires_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When session expires, NULL = no expiry")] | None
    ) = None

    @classmethod
    def get_current(cls) -> dict | None:
        """Return the current session row, or None if no session exists."""
        return cls.read_row()

    @classmethod
    def set_user(cls, user_id: int) -> str:
        """Activate a user session. Returns the new session token."""
        token = secrets.token_urlsafe(32)
        cls.write_row(id=1, user_id=user_id, token=token, started_at=None, expires_at=None)
        return token

    @classmethod
    def clear(cls) -> None:
        """Deselect the current user (keep the row, null out user_id and token)."""
        cls.write_row(id=1, user_id=None, token=None, started_at=None, expires_at=None)

    @classmethod
    def validate_token(cls, token: str | None) -> int | None:
        """Return the user_id for a valid token, or None."""
        if not token:
            return None
        row = cls.read_row()
        if row and row.get("token") == token and row.get("user_id") is not None:
            return row["user_id"]
        return None
