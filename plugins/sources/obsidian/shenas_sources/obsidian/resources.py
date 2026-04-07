"""Parse Obsidian daily notes frontmatter + habit checkboxes into dlt resources."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.obsidian.tables import DailyNote, Habit

if TYPE_CHECKING:
    from collections.abc import Iterator


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


def _date_from_filename(path: Path) -> str | None:
    """Extract YYYY-MM-DD from a daily note filename."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
    return match.group(1) if match else None


_CHECKBOX_RE = re.compile(r"^- \[([ xX])\] (.+)$")
_INLINE_FIELD_RE = re.compile(r"\s*\[([\w_-]+)::\s*([^\]]*)\]")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _parse_habit_line(line: str, date: str) -> dict[str, Any] | None:
    """Parse one top-level checkbox line into a habit row.

    Only matches lines with zero indentation (so nested sub-tasks under
    morning-routine etc. are skipped). Strips inline dataview metadata
    fields and markdown links from the displayed name, captures the URL
    if a link was present, and yields the original raw label too.
    """
    if line[:1] != "-":  # zero-indent only -- nested entries start with whitespace
        return None
    match = _CHECKBOX_RE.match(line)
    if not match:
        return None

    completed = match.group(1).lower() == "x"
    raw = match.group(2)

    # Pull out [scheduled:: ...] and [completion:: ...] dataview fields.
    scheduled: str | None = None
    completion: str | None = None
    for fld_name, fld_value in _INLINE_FIELD_RE.findall(raw):
        if fld_name == "scheduled":
            scheduled = fld_value.strip() or None
        elif fld_name == "completion":
            completion = fld_value.strip() or None

    # Remove all dataview fields from the displayed name.
    name = _INLINE_FIELD_RE.sub("", raw).strip()

    # Extract a markdown link URL if present, then collapse [text](url) -> text.
    url: str | None = None
    link_match = _MD_LINK_RE.search(name)
    if link_match:
        url = link_match.group(2)
        name = _MD_LINK_RE.sub(lambda m: m.group(1), name).strip()

    if not name:
        return None

    return {
        "date": date,
        "name": name,
        "completed": completed,
        "scheduled": scheduled,
        "completion": completion,
        "url": url,
        "raw": raw,
    }


def _extract_habits(text: str, date: str, heading: str) -> Iterator[dict[str, Any]]:
    """Yield habit rows for every top-level checkbox under the given H1/H2 heading.

    The section ends at the next H1/H2 heading or at a horizontal rule (`---`).
    Both `# heading` and `## heading` are accepted; comparison is case-insensitive
    and whitespace-trimmed.
    """
    target = heading.strip().lower()
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()

        # New heading? Decide whether we're entering, leaving, or staying out.
        h_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if h_match:
            level = len(h_match.group(1))
            text_part = h_match.group(2).strip().lower()
            if level <= 2 and text_part == target:
                in_section = True
            elif level <= 2 and in_section:
                # Different H1/H2 -- end of section.
                in_section = False
            continue

        if not in_section:
            continue

        if stripped == "---":
            in_section = False
            continue

        row = _parse_habit_line(line, date)
        if row is not None:
            yield row


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


@dlt.resource(
    write_disposition="merge",
    primary_key=list(DailyNote.__pk__),
    columns=dataclass_to_dlt_columns(DailyNote),
)
def daily_notes(notes_dir: str) -> Iterator[dict[str, Any]]:
    """Yield one row per daily note with frontmatter fields as columns."""
    for date, text in _iter_daily_notes(notes_dir):
        frontmatter = _parse_frontmatter(text)
        if not frontmatter:
            continue

        row: dict[str, Any] = {"date": date}
        for key, value in frontmatter.items():
            if isinstance(value, list):
                row[key] = ", ".join(str(v) for v in value)
            else:
                row[key] = value

        yield row


@dlt.resource(
    name="habits",
    write_disposition="merge",
    primary_key=list(Habit.__pk__),
    columns=dataclass_to_dlt_columns(Habit),
)
def habits(notes_dir: str, heading: str = "Plan for the day") -> Iterator[dict[str, Any]]:
    """Yield one habit row per top-level checkbox under `heading` per daily note."""
    for date, text in _iter_daily_notes(notes_dir):
        yield from _extract_habits(text, date, heading)
