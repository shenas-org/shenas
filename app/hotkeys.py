"""Hotkey bindings persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, ClassVar

from shenas_plugins.core.table import Field, Table

if TYPE_CHECKING:
    import duckdb


@dataclass
class Hotkey(Table):
    """A single keyboard shortcut binding.

    Direct :class:`Table` subclass -- no wrapper. CRUD comes from the
    ABC; ``upsert`` is the natural set / update primitive. ``get_all``
    and ``reset`` are thin views over the inherited ``all``.
    """

    table_name: ClassVar[str] = "hotkeys"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "Hotkeys"
    table_description: ClassVar[str | None] = "Per-action keyboard shortcut bindings."
    table_pk: ClassVar[tuple[str, ...]] = ("action_id",)

    action_id: Annotated[str, Field(db_type="VARCHAR", description="Action identifier")] = ""
    binding: Annotated[str, Field(db_type="VARCHAR", description="Key binding", db_default="''")] = ""
    created_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="When created", db_default="current_timestamp")] | None
    ) = None
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
        """Update the binding for this action and upsert."""
        self.binding = binding
        return self.upsert()

    @classmethod
    def get_all(cls) -> dict[str, str]:
        """Return ``{action_id: binding}`` for every registered hotkey."""
        return {h.action_id: h.binding for h in cls.all(order_by="action_id")}

    @staticmethod
    def seed(con: duckdb.DuckDBPyConnection) -> None:
        """Insert default bindings if the table is empty.

        Runs from ``_ensure_system_tables`` *before* ``app.db.cursor`` is
        wired up to the shared connection -- hence the raw INSERT here
        instead of going through the ABC primitives.
        """
        row = con.execute("SELECT COUNT(*) FROM shenas_system.hotkeys").fetchone()
        if row and row[0] == 0:
            for action_id, binding in Hotkey._DEFAULTS:
                con.execute(
                    "INSERT INTO shenas_system.hotkeys (action_id, binding) VALUES (?, ?)",
                    [action_id, binding],
                )

    @classmethod
    def reset(cls) -> None:
        """Drop every binding and re-seed defaults."""
        from app.db import cursor

        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.hotkeys")
        for action_id, binding in cls._DEFAULTS:
            cls(action_id=action_id, binding=binding).insert()
