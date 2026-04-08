"""Single-row active session: tracks which local user is currently selected."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Annotated, ClassVar

from shenas_plugins.core.table import Field, Table


class LocalSession(Table):
    table_name: ClassVar[str] = "local_sessions"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Local Sessions"
    table_description: ClassVar[str | None] = (
        "Active user session (single row, persists across restarts)."
    )
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
    user_id: (
        Annotated[int, Field(db_type="INTEGER", description="Active user ID")] | None
    ) = None
    token: (
        Annotated[str, Field(db_type="VARCHAR", description="Session token")] | None
    ) = None
    started_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When session started")] | None
    ) = None

    @classmethod
    def get_current(cls) -> dict | None:
        return cls.read_row()

    @classmethod
    def set_user(cls, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        cls.write_row(id=1, user_id=user_id, token=token, started_at=datetime.now().isoformat())
        return token

    @classmethod
    def clear(cls) -> None:
        cls.write_row(id=1, user_id=None, token=None, started_at=None)

    @classmethod
    def validate_token(cls, token: str | None) -> int | None:
        """Return the user_id if the token is valid, otherwise None."""
        if not token:
            return None
        row = cls.read_row()
        if row and row.get("token") == token and row.get("user_id") is not None:
            return int(row["user_id"])
        return None
