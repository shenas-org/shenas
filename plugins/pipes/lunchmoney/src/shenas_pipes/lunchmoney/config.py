from dataclasses import dataclass
from typing import ClassVar

from shenas_pipes.core.base_config import PipeConfig


@dataclass
class LunchMoneyConfig(PipeConfig):
    """Lunch Money pipe configuration."""

    __table__: ClassVar[str] = "pipe_lunchmoney"
