from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pendulum

if TYPE_CHECKING:
    from collections.abc import Iterator


def resolve_start_date(value: str) -> str:
    """Parse 'YYYY-MM-DD' or 'N days ago' into an ISO date string."""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value
    match = re.fullmatch(r"(\d+)\s+days?\s+ago", value.strip())
    if match:
        return pendulum.now().subtract(days=int(match.group(1))).to_date_string()
    raise ValueError(f"Cannot parse start_date: {value!r}. Use 'YYYY-MM-DD' or 'N days ago'.")


def date_range(start: str, end: str | None = None) -> Iterator[str]:
    """Yield ISO date strings from start to end (inclusive, defaults to today)."""
    current = pendulum.parse(start).date()
    stop = pendulum.parse(end).date() if end else pendulum.now().date()
    while current <= stop:
        yield current.to_date_string()
        current = current.add(days=1)


def is_empty_response(data: dict | None, sentinel_key: str = "calendarDate") -> bool:
    """Check if an API response is empty or missing a sentinel key."""
    if not data:
        return True
    return data.get(sentinel_key) is None
