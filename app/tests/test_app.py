import contextlib
from collections.abc import Generator, Iterator
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


class TestIndex:
    @staticmethod
    def _make_fake_ui(tmp_path: Path) -> type:
        from shenas_ui.core import UI

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
