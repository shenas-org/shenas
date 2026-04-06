"""Workspace state persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.db import cursor
from shenas_plugins.core.field import Field


class Workspace:
    """App workspace state (tab layout, active tab, etc.)."""

    @dataclass
    class _Row:
        __table__: ClassVar[str] = "workspace"
        __pk__: ClassVar[tuple[str, ...]] = ("id",)

        id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
        state: Annotated[str, Field(db_type="VARCHAR", description="Workspace state JSON", db_default="'{}'")] = "{}"
        updated_at: (
            Annotated[str, Field(db_type="TIMESTAMP", description="When last updated", db_default="current_timestamp")] | None
        ) = None

    @staticmethod
    def get() -> dict[str, Any]:
        import json

        with cursor() as cur:
            row = cur.execute("SELECT state FROM shenas_system.workspace WHERE id = 1").fetchone()
        if not row:
            return {}
        try:
            return json.loads(row[0])
        except Exception:
            return {}

    @staticmethod
    def save(state: dict[str, Any]) -> None:
        import json

        data = json.dumps(state)
        with cursor() as cur:
            cur.execute(
                "INSERT INTO shenas_system.workspace (id, state, updated_at) VALUES (1, ?, now()) "
                "ON CONFLICT (id) DO UPDATE SET state = excluded.state, updated_at = now()",
                [data],
            )
