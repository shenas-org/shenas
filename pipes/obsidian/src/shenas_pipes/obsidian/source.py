"""Parse Obsidian daily notes frontmatter into dlt resources."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt
import yaml


def _parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Extract YAML frontmatter from a markdown file."""
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


@dlt.resource(write_disposition="merge", primary_key="date")
def daily_notes(notes_dir: str) -> Iterator[dict[str, Any]]:
    """Yield one row per daily note with frontmatter fields as columns."""
    notes_path = Path(notes_dir)
    if not notes_path.is_dir():
        return

    for md_file in sorted(notes_path.glob("*.md")):
        date = _date_from_filename(md_file)
        if not date:
            continue

        text = md_file.read_text(encoding="utf-8")
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
