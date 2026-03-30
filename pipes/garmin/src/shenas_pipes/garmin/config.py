from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.config import BasePipeConfig
from shenas_schemas.core.field import Field


@dataclass
class GarminConfig(BasePipeConfig):
    """Garmin Connect pipe configuration."""

    __table__: ClassVar[str] = "pipe_garmin"

    oauth_tokens: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Serialized garth OAuth tokens (JSON)",
                category="secret",
                ui_widget="password",
            ),
        ]
        | None
    ) = None
    start_date: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Default sync start date",
            default="30 days ago",
            ui_widget="text",
            example_value="30 days ago",
        ),
    ] = "30 days ago"
