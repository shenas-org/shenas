"""Workspace state persistence."""

from __future__ import annotations

from typing import Annotated, Any, ClassVar

from app.db import cursor
from shenas_plugins.core.table import Field, Table


class Workspace:
    """App workspace state (tab layout, active tab, etc.)."""

    class _Table(Table):
        table_name: ClassVar[str] = "workspace"
        table_schema: ClassVar[str | None] = "shenas_system"
        table_display_name: ClassVar[str] = "Workspace"
        table_description: ClassVar[str | None] = "Per-user workspace state (tab layout, active tab, ...)."
        table_pk: ClassVar[tuple[str, ...]] = ("id", "user_id")

        id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
        user_id: Annotated[int, Field(db_type="INTEGER", description="User ID (0 = single-user)", db_default="0")] = 0
        state: Annotated[str, Field(db_type="VARCHAR", description="Workspace state JSON", db_default="'{}'")] = "{}"
        updated_at: (
            Annotated[str, Field(db_type="TIMESTAMP", description="When last updated", db_default="current_timestamp")] | None
        ) = None

    @staticmethod
    def get(user_id: int = 0) -> dict[str, Any]:
        import json

        with cursor() as cur:
            row = cur.execute(
                "SELECT state FROM shenas_system.workspace WHERE id = 1 AND user_id = ?", [user_id]
            ).fetchone()
        if not row:
            return {}
        try:
            return json.loads(row[0])
        except Exception:
            return {}

    @staticmethod
    def save(state: dict[str, Any], user_id: int = 0) -> None:
        import json

        data = json.dumps(state)
        with cursor() as cur:
            cur.execute(
                "INSERT INTO shenas_system.workspace (id, user_id, state, updated_at) VALUES (1, ?, ?, now()) "
                "ON CONFLICT (id, user_id) DO UPDATE SET state = excluded.state, updated_at = now()",
                [user_id, data],
            )
