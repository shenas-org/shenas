"""Database connection for pipes -- delegates to app.db.

All connection management is centralized in app.db. This module
re-exports the public API so pipe code doesn't need to change.
"""

from __future__ import annotations

from app.db import DB_PATH, connect, dlt_destination, get_db_key
from app.db import flush_from_memory as flush_to_encrypted


def close() -> None:
    """No-op. The connection is managed by app.db."""


__all__ = ["DB_PATH", "close", "connect", "dlt_destination", "flush_to_encrypted", "get_db_key"]
