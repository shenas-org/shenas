"""System-wide settings persistence."""

from __future__ import annotations

from typing import Annotated

from app.table import Field, SingletonTable


class SystemSettings(SingletonTable):
    class _Meta:
        name = "system_settings"
        display_name = "System Settings"
        description = "System-wide configuration flags."
        schema = "shenas"
        pk = ("id",)
        database = "system"

    id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
    multiuser_enabled: Annotated[
        bool,
        Field(db_type="BOOLEAN", description="Whether multi-user mode is enabled", db_default="FALSE"),
    ] = False
