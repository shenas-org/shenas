from unittest.mock import patch

import duckdb
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient

import local_frontend.server as server_module
from local_frontend.server import app


@pytest.fixture()
def test_con() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with test data."""
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA metrics")
    con.execute("CREATE TABLE metrics.daily_hrv (date DATE, source VARCHAR, rmssd DOUBLE)")
    con.execute("INSERT INTO metrics.daily_hrv VALUES ('2026-03-15', 'garmin', 42.0)")
    con.execute("CREATE SCHEMA garmin")
    con.execute("CREATE TABLE garmin.activities (id INTEGER, start_time_local DATE)")
    con.execute("INSERT INTO garmin.activities VALUES (1, '2026-03-15')")
    return con


@pytest.fixture()
def client(test_con: duckdb.DuckDBPyConnection) -> TestClient:
    with patch("local_frontend.server.connect", return_value=test_con):
        yield TestClient(app)


class TestIndex:
    def test_returns_html(self, client: TestClient) -> None:
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "shenas ui" in resp.text

    def test_no_components_message(self, client: TestClient) -> None:
        with patch.object(server_module, "_discover_components", return_value=[]):
            resp = client.get("/")
        assert "No components installed" in resp.text

    def test_with_components(self, client: TestClient) -> None:
        fake = [{"name": "test-dash", "version": "1.0", "description": "A test", "html": "test.html"}]
        with patch.object(server_module, "_discover_components", return_value=fake):
            resp = client.get("/")
        assert "test-dash" in resp.text
        assert "v1.0" in resp.text


class TestApiTables:
    def test_lists_tables(self, client: TestClient) -> None:
        resp = client.get("/api/tables")
        assert resp.status_code == 200
        data = resp.json()
        schemas = {(r["schema"], r["table"]) for r in data}
        assert ("metrics", "daily_hrv") in schemas
        assert ("garmin", "activities") in schemas


class TestApiQuery:
    def test_valid_query(self, client: TestClient) -> None:
        resp = client.get("/api/query?sql=SELECT * FROM metrics.daily_hrv")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.apache.arrow.stream"
        table = pa.ipc.open_stream(resp.content).read_all()
        assert table.num_rows == 1
        assert "rmssd" in table.schema.names

    def test_invalid_sql(self, client: TestClient) -> None:
        resp = client.get("/api/query?sql=SELECT * FROM nonexistent")
        assert resp.status_code == 400
        assert "text/plain" in resp.headers["content-type"]

    def test_arrow_roundtrip(self, client: TestClient) -> None:
        resp = client.get("/api/query?sql=SELECT rmssd FROM metrics.daily_hrv")
        table = pa.ipc.open_stream(resp.content).read_all()
        assert table.column("rmssd").to_pylist() == [42.0]
