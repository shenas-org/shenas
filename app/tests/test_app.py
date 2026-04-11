import contextlib
from collections.abc import Generator, Iterator
from pathlib import Path
from unittest.mock import patch

import duckdb
import pyarrow as pa
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from app.main import app

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
    def _fake_cursor(**_kwargs) -> Generator[duckdb.DuckDBPyConnection, None, None]:
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
        from shenas_frontends.core import Frontend

        class FakeUI(Frontend):
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
        with patch("app.api.sources._load_frontends", return_value=fake_ui):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "test ui" in resp.text

    def test_fallback_when_no_ui(self, client: TestClient) -> None:
        with patch("app.api.sources._load_frontends", return_value=[]):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "not installed" in resp.text

    def test_spa_fallback(self, client: TestClient, tmp_path: Path) -> None:
        html_file = tmp_path / "default.html"
        html_file.write_text("<html><body>spa shell</body></html>")
        fake_ui = [self._make_fake_ui(tmp_path)]
        with patch("app.api.sources._load_frontends", return_value=fake_ui):
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


class TestGetActiveTheme:
    """Tests for app.main._get_active_theme."""

    @staticmethod
    def _make_theme(name: str, css: str = "style.css") -> type:
        from shenas_themes.core import Theme

        ns = {"name": name, "display_name": name.title(), "static_dir": Path("/fake"), "css": css, "html": ""}
        return type(f"Theme_{name}", (Theme,), ns)

    def test_returns_enabled_theme_from_db(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        from app.main import _get_active_theme

        dark = self._make_theme("dark")
        light = self._make_theme("light")

        # Set up plugin state in the test DB
        test_con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
        from app.db import _ensure_system_tables

        _ensure_system_tables(test_con)
        test_con.execute("INSERT INTO shenas_system.plugins (kind, name, enabled) VALUES ('theme', 'dark', true)")
        test_con.execute("INSERT INTO shenas_system.plugins (kind, name, enabled) VALUES ('theme', 'light', false)")

        with (
            patch("app.api.sources._load_themes", return_value=[dark, light]),
            patch("app.db.connect", return_value=test_con),
        ):
            result = _get_active_theme()
        assert result is dark

    def test_falls_back_to_default_theme(self, client: TestClient) -> None:
        from app.main import _get_active_theme

        default = self._make_theme("default")
        other = self._make_theme("other")
        with (
            patch("app.api.sources._load_themes", return_value=[default, other]),
            patch("app.db.connect", side_effect=Exception("no DB")),
        ):
            result = _get_active_theme()
        assert result is default

    def test_falls_back_to_first_theme_if_default_missing(self, client: TestClient) -> None:
        from app.main import _get_active_theme

        custom = self._make_theme("custom")
        app.state.default_theme = "nonexistent"
        with (
            patch("app.api.sources._load_themes", return_value=[custom]),
            patch("app.db.connect", side_effect=Exception("no DB")),
        ):
            result = _get_active_theme()
        assert result is custom
        app.state.default_theme = "default"

    def test_returns_none_when_no_themes(self, client: TestClient) -> None:
        from app.main import _get_active_theme

        with patch("app.api.sources._load_themes", return_value=[]):
            result = _get_active_theme()
        assert result is None

    def test_falls_back_on_db_error(self, client: TestClient) -> None:
        from app.main import _get_active_theme

        default = self._make_theme("default")
        with (
            patch("app.api.sources._load_themes", return_value=[default]),
            patch("app.db.connect", side_effect=Exception("DB down")),
        ):
            result = _get_active_theme()
        assert result is default


class TestServeUiHtml:
    @staticmethod
    def _make_fake_ui(tmp_path: Path, name: str = "default") -> type:
        from shenas_frontends.core import Frontend

        class FakeUI(Frontend):
            pass

        FakeUI.name = name
        FakeUI.display_name = name.title()
        FakeUI.static_dir = tmp_path
        FakeUI.html = f"{name}.html"
        FakeUI.entrypoint = f"{name}.js"
        return FakeUI

    def test_injects_theme_css(self, client: TestClient, tmp_path: Path) -> None:
        html_file = tmp_path / "default.html"
        html_file.write_text("<html><head></head><body>themed</body></html>")
        fake_ui = [self._make_fake_ui(tmp_path)]

        from shenas_themes.core import Theme

        class FakeTheme(Theme):
            name = "dark"
            display_name = "Dark"
            static_dir = tmp_path
            css = "dark.css"
            html = ""

        with (
            patch("app.api.sources._load_frontends", return_value=fake_ui),
            patch("app.main._get_active_theme", return_value=FakeTheme),
        ):
            resp = client.get("/")
        assert resp.status_code == 200
        assert '/themes/dark/dark.css"' in resp.text
        assert "data-shenas-theme" in resp.text

    def test_no_theme_injection_when_none(self, client: TestClient, tmp_path: Path) -> None:
        html_file = tmp_path / "default.html"
        html_file.write_text("<html><head></head><body>plain</body></html>")
        fake_ui = [self._make_fake_ui(tmp_path)]
        with (
            patch("app.api.sources._load_frontends", return_value=fake_ui),
            patch("app.main._get_active_theme", return_value=None),
        ):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "data-shenas-theme" not in resp.text
        assert "plain" in resp.text

    def test_uses_db_enabled_ui(self, client: TestClient, tmp_path: Path) -> None:
        """When a Frontend reports enabled, that one is used instead of env default."""
        html_file = tmp_path / "custom.html"
        html_file.write_text("<html><body>custom ui</body></html>")
        default_ui = self._make_fake_ui(tmp_path, "default")
        custom_ui = self._make_fake_ui(tmp_path, "custom")

        class _FakeInstance:
            def __init__(self, enabled: bool) -> None:
                self.enabled = enabled

        def _fake_find(kind: str, name: str):
            return _FakeInstance(enabled=(name == "custom"))

        with (
            patch("app.api.sources._load_frontends", return_value=[default_ui, custom_ui]),
            patch("shenas_plugins.core.plugin.PluginInstance.find", side_effect=_fake_find),
            patch("app.main._get_active_theme", return_value=None),
        ):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "custom ui" in resp.text

    def test_fallback_html_when_ui_html_missing(self, client: TestClient, tmp_path: Path) -> None:
        """Frontend exists but its HTML file is missing -> fallback."""
        fake_ui = self._make_fake_ui(tmp_path, "broken")
        # Don't create the HTML file
        with patch("app.api.sources._load_frontends", return_value=[fake_ui]):
            app.state.ui_name = "broken"
            resp = client.get("/")
            app.state.ui_name = "default"
        assert resp.status_code == 200
        assert "not installed" in resp.text


class TestShenasCLI:
    def test_no_cert(self, tmp_path: Path) -> None:
        from app.cli import app as shenas_app

        result = runner.invoke(
            shenas_app,
            ["--cert", str(tmp_path / "nonexistent.pem"), "--key", str(tmp_path / "nonexistent.key")],
            catch_exceptions=False,
        )
        assert result.exit_code == 1
        assert "TLS certificate not found" in result.output
