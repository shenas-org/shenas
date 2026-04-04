from dataclasses import dataclass
from typing import ClassVar

from shenas_pipes.core.base_config import PipeConfig


@dataclass
class GcalendarConfig(PipeConfig):
    """Google Calendar pipe configuration."""

    __table__: ClassVar[str] = "pipe_gcalendar"
