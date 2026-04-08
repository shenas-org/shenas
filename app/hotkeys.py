"""Hotkey bindings persistence."""

from __future__ import annotations

from typing import Annotated, ClassVar

from shenas_plugins.core.table import Field, UserTable


class Hotkey:
    """A single keyboard shortcut binding."""

    class _Table(UserTable):
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

    def __init__(self, action_id: str, binding: str = "", user_id: int = 0) -> None:
        self.action_id = action_id
        self.binding = binding
        self.user_id = user_id

    def set(self, binding: str) -> None:
        from datetime import datetime, timezone

        self.binding = binding
        Hotkey._Table.upsert_row(
            self.user_id,
            action_id=self.action_id,
            binding=binding,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def delete(self) -> None:
        Hotkey._Table.delete_row(self.user_id, action_id=self.action_id)

    @staticmethod
    def get_all(user_id: int = 0) -> dict[str, str]:
        rows = Hotkey._Table.read_rows(user_id)
        return {r["action_id"]: r["binding"] for r in rows}

    @staticmethod
    def seed(user_id: int = 0) -> None:
        if not Hotkey._Table.read_rows(user_id):
            for action_id, binding in Hotkey._DEFAULTS:
                Hotkey._Table.upsert_row(user_id, action_id=action_id, binding=binding)

    @staticmethod
    def reset(user_id: int = 0) -> None:
        Hotkey._Table.delete_rows(user_id)
        for action_id, binding in Hotkey._DEFAULTS:
            Hotkey._Table.upsert_row(user_id, action_id=action_id, binding=binding)
