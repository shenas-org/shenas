"""Base config dataclass for all pipes.

Provides the common fields (id, sync_frequency, lookback_period) and class vars (__pk__)
so individual pipes only define their custom fields and __table__.
"""

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_datasets.core.field import Field


@dataclass
class SourceConfig:
    """Base configuration for all pipes."""

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
    lookback_period: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="How far back to look on initial or full-refresh sync, in minutes (unset = pipe default)",
                ui_widget="text",
                example_value="43200",
            ),
        ]
        | None
    ) = None
