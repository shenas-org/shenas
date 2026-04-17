"""Shared test fixtures for dataset plugins.

Import ``db_con`` in each dataset's ``tests/conftest.py`` to wire the
cursor resolver to an in-memory DuckDB for ``Table.ensure()`` calls::

    from shenas_datasets.core.testing import db_con  # noqa: F401
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import duckdb
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


class _StubDB:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def connect(self) -> duckdb.DuckDBPyConnection:
        return self._con

    @contextlib.contextmanager
    def cursor(self) -> Iterator[duckdb.DuckDBPyConnection]:
        cur = self._con.cursor()
        try:
            yield cur
        finally:
            cur.close()


@pytest.fixture
def db_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """In-memory DuckDB with cursor resolver wired for Table.ensure()."""
    import app.database
    import app.db

    con = duckdb.connect()
    con.execute("CREATE SCHEMA IF NOT EXISTS metrics")
    stub = _StubDB(con)
    saved = dict(app.db._resolvers)
    app.db._resolvers[None] = lambda: stub  # ty: ignore[invalid-assignment]
    yield con
    app.db._resolvers.clear()
    app.db._resolvers.update(saved)
    con.close()
