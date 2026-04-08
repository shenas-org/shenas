"""Hotkey bindings persistence (per-user when multi-user mode is active)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, ClassVar

from app.db import cursor
from shenas_plugins.core.table import Field, Table

if TYPE_CHECKING:
    import duckdb


class Hotkey:
    """A single keyboard shortcut binding."""

    class _Table(Table):
        table_name: ClassVar[str] = "hotkeys"
        table_schema: ClassVar[str | None] = "shenas_system"
        table_display_name: ClassVar[str] = "Hotkeys"
        table_description: ClassVar[str | None] = "Per-action keyboard shortcut bindings per user."
        table_pk: ClassVar[tuple[str, ...]] = ("action_id", "user_id")

        action_id: Annotated[str, Field(db_type="VARCHAR", description="Action identifier")] = ""
        user_id: Annotated[int, Field(db_type="INTEGER", description="User ID (0 = single-user)")] = 0
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

    def __init__(self, action_id: str, binding: str = "") -> None:
        self.action_id = action_id
        self.binding = binding

    def set(self, binding: str) -> None:
        from app.user_context import get_current_user_id

        self.binding = binding
        uid = get_current_user_id()
        with cursor() as cur:
            cur.execute(
                "INSERT INTO shenas_system.hotkeys (action_id, user_id, binding, updated_at) VALUES (?, ?, ?, now()) "
                "ON CONFLICT (action_id, user_id) DO UPDATE SET binding = ?, updated_at = now()",
                [self.action_id, uid, binding, binding],
            )

    def delete(self) -> None:
        from app.user_context import get_current_user_id

        uid = get_current_user_id()
        with cursor() as cur:
            cur.execute(
                "DELETE FROM shenas_system.hotkeys WHERE action_id = ? AND user_id = ?",
                [self.action_id, uid],
            )

    @staticmethod
    def get_all() -> dict[str, str]:
        from app.user_context import get_current_user_id

        uid = get_current_user_id()
        with cursor() as cur:
            rows = cur.execute(
                "SELECT action_id, binding FROM shenas_system.hotkeys WHERE user_id = ? ORDER BY action_id",
                [uid],
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def seed(con: duckdb.DuckDBPyConnection, user_id: int = 0) -> None:
        row = con.execute(
            "SELECT COUNT(*) FROM shenas_system.hotkeys WHERE user_id = ?", [user_id]
        ).fetchone()
        if row and row[0] == 0:
            for action_id, binding in Hotkey._DEFAULTS:
                con.execute(
                    "INSERT INTO shenas_system.hotkeys (action_id, user_id, binding) VALUES (?, ?, ?)",
                    [action_id, user_id, binding],
                )

    @staticmethod
    def reset() -> None:
        from app.user_context import get_current_user_id

        uid = get_current_user_id()
        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.hotkeys WHERE user_id = ?", [uid])
            for action_id, binding in Hotkey._DEFAULTS:
                cur.execute(
                    "INSERT INTO shenas_system.hotkeys (action_id, user_id, binding) VALUES (?, ?, ?)",
                    [action_id, uid, binding],
                )
