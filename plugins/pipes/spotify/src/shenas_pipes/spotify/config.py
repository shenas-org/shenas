from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.base_config import PipeConfig
from shenas_schemas.core.field import Field


@dataclass
class SpotifyConfig(PipeConfig):
    """Spotify pipe configuration."""

    __table__: ClassVar[str] = "pipe_spotify"

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
