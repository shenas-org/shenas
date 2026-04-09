"""Hotkey bindings persistence: per-user keyboard shortcuts.

Lives in each user's encrypted DB, so rows are not keyed by user_id --
each user only ever sees their own bindings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, ClassVar

import duckdb  # noqa: TC002 - runtime type for seed() parameter

from shenas_plugins.core.table import Field, Table


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Hotkey(Table):
    """A single keyboard shortcut binding for one action."""

    class _Meta:
        name = "hotkeys"
        display_name = "Hotkeys"
        description = "Per-action keyboard shortcut bindings."
        schema = "shenas_system"
        pk = ("action_id",)

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

    def set_binding(self, binding: str) -> Hotkey:
        """Update this binding and upsert the row."""
        self.binding = binding
        self.updated_at = _now_iso()
        return self.upsert()

    @classmethod
    def get_all(cls) -> dict[str, str]:
        """Return ``{action_id: binding}``."""
        rows = cls.all(order_by="action_id")
        return {h.action_id: h.binding for h in rows}

    @classmethod
    def seed(cls, con: duckdb.DuckDBPyConnection | None = None) -> None:
        """Insert default bindings if none exist yet.

        Accepts an explicit ``con`` so it can be called from bootstrap
        helpers that don't yet have the resolver wired up.
        """
        if con is not None:
            row = con.execute("SELECT 1 FROM shenas_system.hotkeys LIMIT 1").fetchone()
            if row:
                return
            for action_id, binding in cls._DEFAULTS:
                con.execute(
                    "INSERT INTO shenas_system.hotkeys (action_id, binding) VALUES (?, ?)",
                    [action_id, binding],
                )
            return
        if cls.all(limit=1):
            return
        for action_id, binding in cls._DEFAULTS:
            cls(action_id=action_id, binding=binding).insert()

    @classmethod
    def reset(cls) -> None:
        """Drop every binding and re-seed defaults."""
        from app.db import cursor

        with cursor() as cur:
            cur.execute("DELETE FROM shenas_system.hotkeys")
        for action_id, binding in cls._DEFAULTS:
            cls(action_id=action_id, binding=binding).insert()
