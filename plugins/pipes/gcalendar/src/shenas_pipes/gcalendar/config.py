from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field


@dataclass
class GcalendarConfig:
    """Google Calendar pipe configuration."""

    __table__: ClassVar[str] = "pipe_gcalendar"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Config row identifier")] = 1
    sync_frequency: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Sync frequency in minutes (unset = no scheduled sync)",
                ui_widget="text",
                example_value="60",
            ),
        ]
        | None
    ) = None
