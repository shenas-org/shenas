"""System-wide settings persistence."""

from __future__ import annotations

from typing import Annotated, ClassVar

from shenas_plugins.core.table import Field, Table


class SystemSettings(Table):
    """System-wide configuration flags (single row)."""

    table_name: ClassVar[str] = "system_settings"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "System Settings"
    table_description: ClassVar[str | None] = "System-wide configuration flags."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
    multiuser_enabled: Annotated[
        bool, Field(db_type="BOOLEAN", description="Enable multi-user mode", db_default="false")
    ] = False
    updated_at: (
        Annotated[str, Field(db_type="TIMESTAMP", description="Last updated", db_default="current_timestamp")] | None
    ) = None

    @classmethod
    def get(cls) -> dict:
        row = cls.read_row()
        return row if row else {"id": 1, "multiuser_enabled": False, "updated_at": None}

    @classmethod
    def set_multiuser(cls, enabled: bool) -> None:
        cls.write_row(id=1, multiuser_enabled=enabled)
