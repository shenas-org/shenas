"""System-wide settings persistence."""

from __future__ import annotations

from typing import Annotated, Any

from shenas_plugins.core.table import Field, Table


class SystemSettings(Table):
    class _Meta:
        name = "system_settings"
        display_name = "System Settings"
        description = "System-wide configuration flags."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
    multiuser_enabled: Annotated[
        bool,
        Field(db_type="BOOLEAN", description="Whether multi-user mode is enabled", db_default="FALSE"),
    ] = False

    @classmethod
    def get(cls) -> dict[str, Any]:
        row = cls.read_row()
        if row is None:
            return {"id": 1, "multiuser_enabled": False}
        return row

    @classmethod
    def put(cls, *, multiuser_enabled: bool) -> None:
        cls.write_row(id=1, multiuser_enabled=multiuser_enabled)
