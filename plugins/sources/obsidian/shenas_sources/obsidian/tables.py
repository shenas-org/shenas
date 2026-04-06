"""Obsidian daily notes raw table schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_datasets.core.field import Field


@dataclass
class DailyNote:
    """Obsidian daily note with frontmatter fields.

    Only the date field is defined here -- frontmatter fields
    vary per user and are handled dynamically by dlt.
    """

    __table__: ClassVar[str] = "daily_notes"
    __pk__: ClassVar[tuple[str, ...]] = ("date",)

    date: Annotated[str, Field(db_type="DATE", description="Daily note date from filename")]
