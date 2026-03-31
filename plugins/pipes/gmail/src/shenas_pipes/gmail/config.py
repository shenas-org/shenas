from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field


@dataclass
class GmailConfig:
    """Gmail pipe configuration."""

    __table__: ClassVar[str] = "pipe_gmail"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Config row identifier")] = 1
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
