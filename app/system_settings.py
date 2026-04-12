"""System-wide settings persistence."""

from __future__ import annotations

from typing import Annotated, ClassVar

from shenas_plugins.core.table import Field, SingletonTable


class SystemSettings(SingletonTable):
    database: ClassVar[str] = "system"

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
