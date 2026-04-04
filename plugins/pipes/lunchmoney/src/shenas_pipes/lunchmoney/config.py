from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.base_config import PipeConfig
from shenas_schemas.core.field import Field


@dataclass
class LunchMoneyConfig(PipeConfig):
    """Lunch Money pipe configuration."""

    __table__: ClassVar[str] = "pipe_lunchmoney"

    api_key: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Lunch Money API access token",
                category="secret",
                ui_widget="password",
            ),
        ]
        | None
    ) = None
