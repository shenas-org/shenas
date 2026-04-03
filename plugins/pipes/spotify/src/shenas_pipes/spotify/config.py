from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field


@dataclass
class SpotifyConfig:
    """Spotify pipe configuration."""

    __table__: ClassVar[str] = "pipe_spotify"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Config row identifier")] = 1
    time_range: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Time range for top tracks/artists: short_term, medium_term, long_term",
            default="medium_term",
            ui_widget="text",
            example_value="medium_term",
        ),
    ] = "medium_term"
    sync_frequency: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Sync frequency in minutes (unset = no scheduled sync). Poll frequently (~60-120 min) to build complete listening history.",
                ui_widget="text",
                example_value="90",
            ),
        ]
        | None
    ) = None
