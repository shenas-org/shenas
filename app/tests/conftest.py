"""Shared test fixtures for app tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import duckdb
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


class _StubDB:
    """Test DB wrapper that yields a single shared in-memory connection."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def connect(self) -> duckdb.DuckDBPyConnection:
        return self._con

    def cursor(self):
        import contextlib

        @contextlib.contextmanager
        def _cm():
            cur = self._con.cursor()
            cur.execute("USE db")
            try:
                yield cur
            finally:
                cur.close()

        return _cm()

    def close(self) -> None:
        pass


@pytest.fixture
def db_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """In-memory DuckDB with system tables initialized."""
    import app.databases
    import app.db

    con = duckdb.connect()
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    stub = _StubDB(con)
    saved = dict(app.databases._resolvers)
    app.databases._resolvers["shenas"] = lambda: stub  # ty: ignore[invalid-assignment]
    app.databases._resolvers[None] = lambda: stub  # ty: ignore[invalid-assignment]
    app.db._ensure_system_tables(con)
    yield con
    app.databases._resolvers.clear()
    app.databases._resolvers.update(saved)
    con.close()


@pytest.fixture
def patch_db(db_con: duckdb.DuckDBPyConnection) -> Iterator[None]:
    """Back-compat alias -- db_con already wires the resolvers."""
    return  # ty: ignore[invalid-return-type]


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
