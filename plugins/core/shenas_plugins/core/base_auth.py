"""Base auth dataclass for all pipes.

Provides the common fields (id) and class vars (__pk__)
so individual pipes only define their credential fields and __table__.
"""

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field


@dataclass
class SourceAuth:
    """Base authentication storage for all pipes."""

    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Auth row identifier")] = 1
