from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.base_config import PipeConfig
from shenas_schemas.core.field import Field


@dataclass
class GtakeoutConfig(PipeConfig):
    """Google Takeout pipe configuration."""

    __table__: ClassVar[str] = "pipe_gtakeout"

    latest: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="Only process the N most recent archives (0 = all)",
            default="0",
            ui_widget="text",
            example_value="0",
        ),
    ] = 0
    name_filter: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Only process archives matching this substring (e.g. '.tgz')",
            default="",
            ui_widget="text",
            example_value=".tgz",
        ),
    ] = ""
