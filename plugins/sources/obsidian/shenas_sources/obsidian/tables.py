"""Obsidian source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. Notable design choices:

- ``DailyNotes`` is an ``AggregateTable`` keyed on ``date``. Frontmatter
  fields are dynamic per user, so only ``date`` is declared on the
  schema -- dlt picks up the rest from the yielded rows.
- ``Habits`` is an ``EventTable`` keyed on ``(date, habit_name)``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.table import Field
from shenas_sources.core.table import (
    AggregateTable,
    EventTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Shared filesystem helpers (used by both DailyNotes and Habits)
# ---------------------------------------------------------------------------


def _date_from_filename(path: Path) -> str | None:
    """Extract YYYY-MM-DD from a daily note filename."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
    return match.group(1) if match else None


def _iter_daily_notes(notes_dir: str) -> Iterator[tuple[str, str]]:
    """Yield (date, file_text) for every dated markdown file in the folder."""
    notes_path = Path(notes_dir)
    if not notes_path.is_dir():
        return
    for md_file in sorted(notes_path.glob("*.md")):
        date = _date_from_filename(md_file)
        if not date:
            continue
        yield date, md_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class DailyNotes(AggregateTable):
    """Obsidian daily note with frontmatter fields.

    Only the ``date`` column is declared here -- frontmatter keys vary per
    user and dlt picks up the rest from the yielded rows.
    """

    class _Meta:
        name = "daily_notes"
        display_name = "Daily Notes"
        description = "Frontmatter fields from Obsidian daily notes."
        pk = ("date",)

    time_at: ClassVar[str] = "date"

    date: Annotated[str, Field(db_type="DATE", description="Daily note date from filename")] = ""

    @staticmethod
    def _parse_frontmatter(text: str) -> dict[str, Any] | None:
        """Extract YAML frontmatter from a markdown file."""
        import yaml

        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return None
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None

    @classmethod
    def extract(cls, client: str, **_: Any) -> Iterator[dict[str, Any]]:
        for date, text in _iter_daily_notes(client):
            frontmatter = cls._parse_frontmatter(text)
            if not frontmatter:
                continue
            row: dict[str, Any] = {"date": date}
            for key, value in frontmatter.items():
                if isinstance(value, list):
                    row[key] = ", ".join(str(v) for v in value)
                else:
                    row[key] = value
            yield row


class Habits(EventTable):
    """One row per top-level checkbox under the configured habits heading."""

    class _Meta:
        name = "habits"
        display_name = "Habits"
        description = "Top-level checkboxes under the configured habits heading."
        pk = ("date", "habit_name")

    time_at: ClassVar[str] = "date"

    date: Annotated[str, Field(db_type="DATE", description="Daily note date from filename")] = ""
    habit_name: Annotated[str, Field(db_type="VARCHAR", description="Checkbox label, links + metadata stripped")] = ""
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

    _CHECKBOX_RE: ClassVar[re.Pattern[str]] = re.compile(r"^- \[([ xX])\] (.+)$")
    _INLINE_FIELD_RE: ClassVar[re.Pattern[str]] = re.compile(r"\s*\[([\w_-]+)::\s*([^\]]*)\]")
    _MD_LINK_RE: ClassVar[re.Pattern[str]] = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    @classmethod
    def _parse_habit_line(cls, line: str, date: str) -> dict[str, Any] | None:
        """Parse one top-level checkbox line into a habit row."""
        if line[:1] != "-":
            return None
        match = cls._CHECKBOX_RE.match(line)
        if not match:
            return None

        completed = match.group(1).lower() == "x"
        raw = match.group(2)

        scheduled: str | None = None
        completion: str | None = None
        for fld_name, fld_value in cls._INLINE_FIELD_RE.findall(raw):
            if fld_name == "scheduled":
                scheduled = fld_value.strip() or None
            elif fld_name == "completion":
                completion = fld_value.strip() or None

        name = cls._INLINE_FIELD_RE.sub("", raw).strip()

        url: str | None = None
        link_match = cls._MD_LINK_RE.search(name)
        if link_match:
            url = link_match.group(2)
            name = cls._MD_LINK_RE.sub(lambda m: m.group(1), name).strip()

        if not name:
            return None

        return {
            "date": date,
            "habit_name": name,
            "completed": completed,
            "scheduled": scheduled,
            "completion": completion,
            "url": url,
            "raw": raw,
        }

    @classmethod
    def _extract_habits(cls, text: str, date: str, heading: str) -> Iterator[dict[str, Any]]:
        """Yield habit rows for every top-level checkbox under the given H1/H2 heading."""
        target = heading.strip().lower()
        in_section = False
        for line in text.splitlines():
            stripped = line.strip()

            h_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
            if h_match:
                level = len(h_match.group(1))
                text_part = h_match.group(2).strip().lower()
                if level <= 2 and text_part == target:
                    in_section = True
                elif level <= 2 and in_section:
                    in_section = False
                continue

            if not in_section:
                continue

            if stripped == "---":
                in_section = False
                continue

            row = cls._parse_habit_line(line, date)
            if row is not None:
                yield row

    @classmethod
    def extract(cls, client: str, *, heading: str = "Plan for the day", **_: Any) -> Iterator[dict[str, Any]]:
        for date, text in _iter_daily_notes(client):
            yield from cls._extract_habits(text, date, heading)


TABLES: tuple[type, ...] = (DailyNotes, Habits)
