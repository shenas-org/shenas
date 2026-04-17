"""Active session persistence -- single row, survives restarts."""

from __future__ import annotations

import secrets
from typing import Annotated, Any

from app.table import Field, SingletonTable


class LocalSession(SingletonTable):
    """Persists the currently active local user across restarts.

    Always a single row (id=1). ``token`` is a random URL-safe string stored
    in the browser's localStorage and validated here on every request.
    """

    class _Meta:
        name = "local_sessions"
        display_name = "Local Sessions"
        description = "Active user session (single row, persists across restarts)."
        schema = "shenas"
        pk = ("id",)
        database = "system"

    id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
    user_id: Annotated[int | None, Field(db_type="INTEGER", description="FK to local_users.id")] = None
    token: Annotated[str | None, Field(db_type="VARCHAR", description="Random session token")] = None
    started_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When session was started")] = None

    @classmethod
    def get_current(cls) -> dict[str, Any] | None:
        """Return the active session row, or None if no user is selected."""
        return cls.read_row()

    @classmethod
    def set_user(cls, user_id: int) -> str:
        """Activate a user session. Returns the new session token."""
        token = secrets.token_urlsafe(32)
        cls.write_row(id=1, user_id=user_id, token=token, started_at=None)
        return token

    @classmethod
    def clear(cls) -> None:
        """Deselect the current user (keep the row, clear user_id and token)."""
        cls.write_row(id=1, user_id=None, token=None, started_at=None)

    @classmethod
    def validate_token(cls, token: str | None) -> int | None:
        """Return the user_id if the token matches the stored session, else None."""
        if not token:
            return None
        row = cls.read_row()
        if row and row.get("token") == token and row.get("user_id") is not None:
            return int(row["user_id"])
        return None
