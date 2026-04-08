"""Obsidian daily notes raw table schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class DailyNote:
    """Obsidian daily note with frontmatter fields.

    Only the date field is defined here -- frontmatter fields
    vary per user and are handled dynamically by dlt.
    """

    __table__: ClassVar[str] = "daily_notes"
    __pk__: ClassVar[tuple[str, ...]] = ("date",)
    __kind__: ClassVar[TableKind] = "aggregate"

    date: Annotated[str, Field(db_type="DATE", description="Daily note date from filename")]


@dataclass
class Habit:
    """A single top-level checkbox under the configured habits heading
    in an Obsidian daily note (default: '# Plan for the day').

    One row per (date, name). Captures completion state plus the dataview-style
    [scheduled:: YYYY-MM-DD] / [completion:: YYYY-MM-DD] inline fields and any
    embedded markdown link URL.
    """

    __table__: ClassVar[str] = "habits"
    __pk__: ClassVar[tuple[str, ...]] = ("date", "name")
    __kind__: ClassVar[TableKind] = "event"

    date: Annotated[str, Field(db_type="DATE", description="Daily note date from filename")]
    name: Annotated[str, Field(db_type="VARCHAR", description="Checkbox label, links + metadata stripped")]
    completed: Annotated[bool, Field(db_type="BOOLEAN", description="Whether the checkbox is ticked")] = False
    scheduled: Annotated[
        str | None,
        Field(db_type="DATE", description="From [scheduled:: YYYY-MM-DD]"),
    ] = None
    completion: Annotated[
        str | None,
        Field(db_type="DATE", description="From [completion:: YYYY-MM-DD]"),
    ] = None
    url: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Embedded markdown link URL if any"),
    ] = None
    raw: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="The full original checkbox label"),
    ] = None
