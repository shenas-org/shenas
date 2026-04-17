"""Hotkey bindings persistence: per-user keyboard shortcuts.

Lives in each user's encrypted DB, so rows are not keyed by user_id --
each user only ever sees their own bindings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, ClassVar

from app.table import Field, Table


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Hotkey(Table):
    """A single keyboard shortcut binding for one action."""

    class _Meta:
        name = "hotkeys"
        display_name = "Hotkeys"
        description = "Per-action keyboard shortcut bindings."
        schema = "ui"
        pk = ("action_id",)

    action_id: Annotated[str, Field(db_type="VARCHAR", description="Action identifier")] = ""
    binding: Annotated[str, Field(db_type="VARCHAR", description="Key binding", db_default="''")] = ""
    updated_at: (
        Annotated[
            str,
            Field(
                db_type="TIMESTAMP",
                description="When last updated",
                db_default="current_timestamp",
            ),
        ]
        | None
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
    def seed(cls) -> None:
        """Insert default bindings if none exist yet."""
        if cls.all(limit=1):
            return
        for action_id, binding in cls._DEFAULTS:
            cls(action_id=action_id, binding=binding).insert()

    @classmethod
    def reset(cls) -> None:
        """Drop every binding and re-seed defaults."""
        for h in cls.all():
            h.delete()
        for action_id, binding in cls._DEFAULTS:
            cls(action_id=action_id, binding=binding).insert()
