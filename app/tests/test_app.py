from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import duckdb
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import app.server as server_module
from app.server import app

runner = CliRunner()


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
def client(test_con: duckdb.DuckDBPyConnection) -> Iterator[TestClient]:
    with patch("app.api.query.connect", return_value=test_con):
        with patch("app.api.db.connect", return_value=test_con):
            yield TestClient(app)


class TestIndex:
    def test_redirects_to_ui(self, client: TestClient) -> None:
        fake_ui = [{"name": "default", "version": "1.0", "static_dir": "/tmp", "html": "default.html"}]
        with patch.object(server_module, "_discover_plugins", return_value=fake_ui):
            resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 307
        assert "/ui/default/default.html" in resp.headers["location"]

    def test_fallback_when_no_ui(self, client: TestClient) -> None:
        with patch.object(server_module, "_discover_plugins", return_value=[]):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "not installed" in resp.text


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


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


class TestDbStatus:
    def test_db_status(self, client: TestClient) -> None:
        with patch("app.api.db.DB_PATH") as mock_path:
            mock_path.exists.return_value = False
            mock_path.__str__ = lambda _: "data/shenas.duckdb"
            resp = client.get("/api/db/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "key_source" in data
        assert "db_path" in data

    def test_db_status_with_tables(self, client: TestClient) -> None:
        with patch("app.api.db.DB_PATH") as mock_path:
            mock_path.exists.return_value = True
            mock_path.stat.return_value.st_size = 1024 * 1024
            mock_path.__str__ = lambda _: "data/shenas.duckdb"
            resp = client.get("/api/db/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["size_mb"] is not None
        schemas = {s["name"] for s in data["schemas"]}
        assert "metrics" in schemas
        assert "garmin" in schemas


class TestShenasCLI:
    def test_no_cert(self, tmp_path: Path) -> None:
        from app.server_cli import app as shenas_app

        result = runner.invoke(
            shenas_app,
            ["--cert", str(tmp_path / "nonexistent.pem"), "--key", str(tmp_path / "nonexistent.key")],
            catch_exceptions=False,
        )
        assert result.exit_code == 1
        assert "TLS certificate not found" in result.output
