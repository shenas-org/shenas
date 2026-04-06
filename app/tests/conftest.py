"""Shared test fixtures for app tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import duckdb
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def db_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """In-memory DuckDB with system tables initialized."""
    con = duckdb.connect()
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    from app.db import _ensure_system_tables

    _ensure_system_tables(con)
    yield con
    con.close()


@pytest.fixture
def patch_db(db_con: duckdb.DuckDBPyConnection) -> Iterator[None]:
    """Patch app.db.connect and app.db._con to use the test connection."""
    with patch("app.db.connect", return_value=db_con), patch("app.db._con", db_con):
        yield


def parse_sse(text: str) -> list[dict]:
    """Parse SSE text into a list of {_event, ...data} dicts."""
    events = []
    event_type = "message"
    for raw_line in text.strip().split("\n"):
        line = raw_line.strip()
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            data = json.loads(line[5:].strip())
            data["_event"] = event_type
            events.append(data)
            event_type = "message"
    return events
