"""Database connection for sources -- delegates to app.db.

All connection management is centralized in app.db. This module
re-exports the public API so source code doesn't need to change.
"""

from __future__ import annotations

from app.database import SHENAS_DB_PATH as DB_PATH
from app.database import connect, dlt_destination, flush_to_encrypted, get_db_key


def close() -> None:
    """No-op. The connection is managed by app.db."""


__all__ = ["DB_PATH", "close", "connect", "dlt_destination", "flush_to_encrypted", "get_db_key"]
