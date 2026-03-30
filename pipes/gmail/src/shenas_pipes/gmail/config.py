from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.config import BasePipeConfig
from shenas_schemas.core.field import Field


@dataclass
class GmailConfig(BasePipeConfig):
    """Gmail pipe configuration."""

    __table__: ClassVar[str] = "pipe_gmail"

    oauth_token: (
        Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Gmail OAuth2 token (JSON)",
                category="secret",
                ui_widget="password",
            ),
        ]
        | None
    ) = None
    default_query: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Default Gmail search query for sync",
            default="",
            ui_widget="text",
            example_value="after:2026/01/01",
        ),
    ] = ""
