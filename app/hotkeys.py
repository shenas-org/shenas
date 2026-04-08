"""Hotkey bindings persistence: per-user keyboard shortcuts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, ClassVar

import duckdb  # noqa: TC002 - runtime type for seed() parameter

from shenas_plugins.core.table import Field, UserTable


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Hotkey(UserTable):
    """A single keyboard shortcut binding for one (user, action).

    Composite PK is ``(action_id, user_id)``; ``user_id`` is 0 in
    single-user mode. CRUD comes from the :class:`UserTable` ABC.
    """

    table_name: ClassVar[str] = "hotkeys"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Hotkeys"
    table_description: ClassVar[str | None] = "Per-action keyboard shortcut bindings, per user."
    table_pk: ClassVar[tuple[str, ...]] = ("action_id", "user_id")

    action_id: Annotated[str, Field(db_type="VARCHAR", description="Action identifier")] = ""
    user_id: Annotated[int, Field(db_type="INTEGER", description="Local user ID (0 = single-user mode)")] = 0
    binding: Annotated[str, Field(db_type="VARCHAR", description="Key binding", db_default="''")] = ""
    updated_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When last updated", db_default="current_timestamp")] | None
    ) = None

    _DEFAULTS: ClassVar[list[tuple[str, str]]] = [
        ("command-palette", "Ctrl+P"),
        ("navigation-palette", "Ctrl+O"),
        ("close-tab", "Ctrl+W"),
        ("new-tab", "Ctrl+T"),
    ]

    def set_binding(self, binding: str) -> Hotkey:
        """Update this binding and upsert the row."""
        self.binding = binding
        self.updated_at = _now_iso()
        return self.upsert()

    @classmethod
    def get_all(cls, user_id: int = 0) -> dict[str, str]:
        """Return ``{action_id: binding}`` for one user."""
        rows = cls.all(where="user_id = ?", params=[user_id], order_by="action_id")
        return {h.action_id: h.binding for h in rows}

    @classmethod
    def seed(cls, con: duckdb.DuckDBPyConnection | None = None, user_id: int = 0) -> None:
        """Insert default bindings for ``user_id`` if none exist yet.

        Accepts an explicit ``con`` because this runs from
        ``_ensure_system_tables`` *before* ``app.db.cursor`` is wired up
        to the shared connection. When called outside that context,
        leave ``con=None`` and the ABC's CRUD primitives will use the
        regular cursor.
        """
        if con is not None:
            row = con.execute(
                "SELECT 1 FROM shenas_system.hotkeys WHERE user_id = ? LIMIT 1",
                [user_id],
            ).fetchone()
            if row:
                return
            for action_id, binding in cls._DEFAULTS:
                con.execute(
                    "INSERT INTO shenas_system.hotkeys (action_id, user_id, binding) VALUES (?, ?, ?)",
                    [action_id, user_id, binding],
                )
            return
        existing = cls.all(where="user_id = ?", params=[user_id], limit=1)
        if existing:
            return
        for action_id, binding in cls._DEFAULTS:
            cls(action_id=action_id, user_id=user_id, binding=binding).insert()

    @classmethod
    def reset(cls, user_id: int = 0) -> None:
        """Drop every binding for ``user_id`` and re-seed defaults."""
        from app.db import cursor

        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.hotkeys WHERE user_id = ?", [user_id])
        for action_id, binding in cls._DEFAULTS:
            cls(action_id=action_id, user_id=user_id, binding=binding).insert()
