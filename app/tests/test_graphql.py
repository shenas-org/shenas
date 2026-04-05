"""Tests for the GraphQL endpoint."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.server import app


@pytest.fixture
def test_con() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with test data, attached as 'db' like the real server."""
    con = duckdb.connect()
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA metrics")
    con.execute("CREATE TABLE metrics.daily_hrv (date DATE, source VARCHAR, rmssd DOUBLE)")
    con.execute("INSERT INTO metrics.daily_hrv VALUES ('2026-03-15', 'garmin', 42.0)")
    con.execute("CREATE SCHEMA garmin")
    con.execute("CREATE TABLE garmin.activities (id INTEGER, start_time_local DATE)")
    con.execute("INSERT INTO garmin.activities VALUES (1, '2026-03-15')")
    return con


@pytest.fixture
def client(test_con: duckdb.DuckDBPyConnection) -> Iterator[TestClient]:
    @contextlib.contextmanager
    def _fake_cursor() -> Generator[duckdb.DuckDBPyConnection, None, None]:
        cur = test_con.cursor()
        try:
            cur.execute("USE db")
            yield cur
        finally:
            cur.close()

    with (
        patch("app.db.cursor", _fake_cursor),
        patch("app.api.query.cursor", _fake_cursor),
        patch("app.api.db.cursor", _fake_cursor),
    ):
        yield TestClient(app)


def _gql(client: TestClient, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query and return the parsed response."""
    resp = client.post("/graphql", json={"query": query, "variables": variables or {}})
    assert resp.status_code == 200
    return resp.json()


class TestGraphQLQueries:
    def test_tables(self, client: TestClient) -> None:
        result = _gql(client, "{ tables { schema table } }")
        assert "errors" not in result
        tables = result["data"]["tables"]
        schemas = {(t["schema"], t["table"]) for t in tables}
        assert ("metrics", "daily_hrv") in schemas
        assert ("garmin", "activities") in schemas

    def test_theme(self, client: TestClient) -> None:
        result = _gql(client, "{ theme { name css } }")
        assert "errors" not in result
        assert "name" in result["data"]["theme"]

    def test_hotkeys(self, client: TestClient) -> None:
        result = _gql(client, "{ hotkeys }")
        assert "errors" not in result

    def test_workspace(self, client: TestClient) -> None:
        result = _gql(client, "{ workspace }")
        assert "errors" not in result


class TestGraphQLMutations:
    def test_set_hotkey(self, client: TestClient) -> None:
        with patch("app.db.set_hotkey"):
            result = _gql(
                client,
                'mutation { setHotkey(actionId: "test-action", binding: "Ctrl+X") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["setHotkey"]["ok"] is True

    def test_reset_hotkeys(self, client: TestClient) -> None:
        with patch("app.db.reset_hotkeys"):
            result = _gql(client, "mutation { resetHotkeys { ok } }")
        assert "errors" not in result
        assert result["data"]["resetHotkeys"]["ok"] is True

    def test_save_workspace(self, client: TestClient) -> None:
        with patch("app.db.save_workspace"):
            result = _gql(
                client,
                'mutation { saveWorkspace(data: {key: "value"}) { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["saveWorkspace"]["ok"] is True
