from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import duckdb
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from app.server import app

runner = CliRunner()


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
    with patch("app.api.query.connect", return_value=test_con), patch("app.api.db.connect", return_value=test_con):
        yield TestClient(app)


class TestIndex:
    @staticmethod
    def _make_fake_ui(tmp_path: Path) -> type:
        from shenas_pipes.core.abc import UI

        class FakeUI(UI):
            name = "default"
            display_name = "Default"
            static_dir = tmp_path
            html = "default.html"
            entrypoint = "default.js"

        return FakeUI

    def test_serves_ui_html(self, client: TestClient, tmp_path: Path) -> None:
        html_file = tmp_path / "default.html"
        html_file.write_text("<html><body>test ui</body></html>")
        fake_ui = [self._make_fake_ui(tmp_path)]
        with patch("app.api.pipes._load_uis", return_value=fake_ui):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "test ui" in resp.text

    def test_fallback_when_no_ui(self, client: TestClient) -> None:
        with patch("app.api.pipes._load_uis", return_value=[]):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "not installed" in resp.text

    def test_spa_fallback(self, client: TestClient, tmp_path: Path) -> None:
        html_file = tmp_path / "default.html"
        html_file.write_text("<html><body>spa shell</body></html>")
        fake_ui = [self._make_fake_ui(tmp_path)]
        with patch("app.api.pipes._load_uis", return_value=fake_ui):
            resp = client.get("/some/deep/route")
        assert resp.status_code == 200
        assert "spa shell" in resp.text


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
        fake_schemas = {"metrics": ["daily_hrv", "daily_sleep"], "garmin": ["activities"]}
        with (
            patch("app.api.db.DB_PATH") as mock_path,
            patch("app.api.db._discover_schemas", return_value=fake_schemas),
            patch(
                "app.api.db._table_stats",
                side_effect=lambda _c, s, n: __import__("app.models", fromlist=["TableStats"]).TableStats(
                    name=n, rows=10, cols=5
                ),
            ),
        ):
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
