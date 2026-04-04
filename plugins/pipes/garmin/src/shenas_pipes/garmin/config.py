from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.base_config import PipeConfig
from shenas_schemas.core.field import Field


@dataclass
class GarminConfig(PipeConfig):
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
