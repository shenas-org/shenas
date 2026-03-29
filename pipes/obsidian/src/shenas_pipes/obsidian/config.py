from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field


@dataclass
class ObsidianConfig:
    """Obsidian daily notes pipe configuration."""

    __table__: ClassVar[str] = "pipe_obsidian"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Config row identifier")] = 1
    daily_notes_folder: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Path to Obsidian daily notes folder",
                ui_widget="text",
                example_value="/home/user/vault/daily",
            ),
        ]
        | None
    ) = None
