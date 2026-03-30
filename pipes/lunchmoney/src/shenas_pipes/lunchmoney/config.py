from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.config import BasePipeConfig
from shenas_schemas.core.field import Field


@dataclass
class LunchMoneyConfig(BasePipeConfig):
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
    start_date: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Default sync start date",
            default="90 days ago",
            ui_widget="text",
            example_value="90 days ago",
        ),
    ] = "90 days ago"
