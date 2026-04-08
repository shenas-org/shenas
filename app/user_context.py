"""User context ContextVar for per-user schema routing.

All per-user DuckDB schemas are derived from a single ContextVar
(``_current_user_id``) so any code that calls ``user_schema()`` automatically
gets the right schema for the currently-authenticated user without needing an
explicit parameter thread.

Schema convention:
- ``user_schema("garmin")``  → ``"garmin_1"``  when user_id = 1
- ``user_schema("garmin")``  → ``"garmin"``     when user_id = 0 (single-user)
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_current_user_id: ContextVar[int] = ContextVar("current_user_id", default=0)


def get_current_user_id() -> int:
    """Return the current user ID (0 = single-user / no user selected)."""
    return _current_user_id.get()


def user_schema(base: str) -> str:
    """Return the per-user DuckDB schema name for a given base schema name.

    Examples::

        user_schema("garmin")   → "garmin_1"  (uid=1)
        user_schema("auth")     → "auth_1"    (uid=1)
        user_schema("metrics")  → "metrics"   (uid=0, single-user)
    """
    uid = _current_user_id.get()
    return f"{base}_{uid}" if uid else base


@contextmanager
def with_user(user_id: int) -> Iterator[None]:
    """Context manager that sets the current user for the duration of the block.

    Safe to nest. ContextVar tokens are properly reset on exit even if an
    exception is raised.
    """
    token = _current_user_id.set(user_id)
    try:
        yield
    finally:
        _current_user_id.reset(token)
