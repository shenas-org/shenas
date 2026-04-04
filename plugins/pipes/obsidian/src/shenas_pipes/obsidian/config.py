from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.base_config import PipeConfig
from shenas_schemas.core.field import Field


@dataclass
class ObsidianConfig(PipeConfig):
    """Obsidian daily notes pipe configuration."""

    __table__: ClassVar[str] = "pipe_obsidian"

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
