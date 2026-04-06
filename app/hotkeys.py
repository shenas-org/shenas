"""Hotkey bindings persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, ClassVar

from app.db import cursor
from shenas_plugins.core.field import Field

if TYPE_CHECKING:
    import duckdb


class Hotkeys:
    """Keyboard shortcut bindings stored in shenas_system.hotkeys."""

    @dataclass
    class _Row:
        __table__: ClassVar[str] = "hotkeys"
        __pk__: ClassVar[tuple[str, ...]] = ("action_id",)

        action_id: Annotated[str, Field(db_type="VARCHAR", description="Action identifier")] = ""
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

    @staticmethod
    def seed(con: duckdb.DuckDBPyConnection) -> None:
        row = con.execute("SELECT COUNT(*) FROM shenas_system.hotkeys").fetchone()
        if row and row[0] == 0:
            for action_id, binding in Hotkeys._DEFAULTS:
                con.execute(
                    "INSERT INTO shenas_system.hotkeys (action_id, binding) VALUES (?, ?)",
                    [action_id, binding],
                )

    @staticmethod
    def get_all() -> dict[str, str]:
        with cursor() as cur:
            rows = cur.execute("SELECT action_id, binding FROM shenas_system.hotkeys ORDER BY action_id").fetchall()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def set(action_id: str, binding: str) -> None:
        with cursor() as cur:
            cur.execute(
                "INSERT INTO shenas_system.hotkeys (action_id, binding, updated_at) VALUES (?, ?, now()) "
                "ON CONFLICT (action_id) DO UPDATE SET binding = ?, updated_at = now()",
                [action_id, binding, binding],
            )

    @staticmethod
    def delete(action_id: str) -> None:
        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.hotkeys WHERE action_id = ?", [action_id])

    @staticmethod
    def reset() -> None:
        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.hotkeys")
            for action_id, binding in Hotkeys._DEFAULTS:
                cur.execute(
                    "INSERT INTO shenas_system.hotkeys (action_id, binding) VALUES (?, ?)",
                    [action_id, binding],
                )
