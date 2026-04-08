"""System-wide settings persistence."""

from __future__ import annotations

from typing import Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, Table


class SystemSettings(Table):
    table_name: ClassVar[str] = "system_settings"
    table_schema: ClassVar[str | None] = "shenas_system"
    table_display_name: ClassVar[str] = "System Settings"
    table_description: ClassVar[str | None] = "System-wide configuration flags."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

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
    def save(cls, *, multiuser_enabled: bool) -> None:
        cls.write_row(id=1, multiuser_enabled=multiuser_enabled)
