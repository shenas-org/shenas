"""Tests for the GraphQL endpoint."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

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
    con.execute("CREATE SCHEMA shenas_system")
    con.execute("CREATE TABLE shenas_system.hotkeys (action_id VARCHAR PRIMARY KEY, binding VARCHAR, updated_at TIMESTAMP)")
    con.execute("INSERT INTO shenas_system.hotkeys VALUES ('command-palette', 'Ctrl+P', NULL)")
    con.execute("INSERT INTO shenas_system.hotkeys VALUES ('close-tab', 'Ctrl+W', NULL)")
    con.execute("CREATE TABLE shenas_system.workspace (id INTEGER PRIMARY KEY, state TEXT, updated_at TIMESTAMP)")
    con.execute("INSERT INTO shenas_system.workspace VALUES (1, '{}', NULL)")
    con.execute(
        "CREATE TABLE shenas_system.plugins ("
        "kind VARCHAR, name VARCHAR, enabled BOOLEAN DEFAULT TRUE, "
        "added_at TIMESTAMP, updated_at TIMESTAMP, status_changed_at TIMESTAMP, synced_at TIMESTAMP, "
        "PRIMARY KEY (kind, name))"
    )
    con.execute("CREATE SEQUENCE IF NOT EXISTS shenas_system.transform_seq START 1")
    con.execute(
        "CREATE TABLE shenas_system.transforms ("
        "id INTEGER DEFAULT nextval('shenas_system.transform_seq'), "
        "source_duckdb_schema VARCHAR, source_duckdb_table VARCHAR, "
        "target_duckdb_schema VARCHAR, target_duckdb_table VARCHAR, "
        "source_plugin VARCHAR, description VARCHAR DEFAULT '', "
        "sql TEXT, is_default BOOLEAN DEFAULT FALSE, enabled BOOLEAN DEFAULT TRUE, "
        "added_at TIMESTAMP DEFAULT current_timestamp, updated_at TIMESTAMP, "
        "status_changed_at TIMESTAMP, PRIMARY KEY (id))"
    )
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
        patch("app.db.connect", return_value=test_con),
        patch("app.api.query.cursor", _fake_cursor),
        patch("app.api.db.cursor", _fake_cursor),
        patch("app.hotkeys.cursor", _fake_cursor),
        patch("app.transforms.cursor", _fake_cursor),
    ):
        yield TestClient(app)


def _gql(client: TestClient, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query and return the parsed response."""
    resp = client.post("/api/graphql", json={"query": query, "variables": variables or {}})
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

    def test_tables_excludes_staging(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute("CREATE SCHEMA garmin_staging")
        test_con.execute("CREATE TABLE garmin_staging.tmp (id INTEGER)")
        result = _gql(client, "{ tables { schema table } }")
        schemas = [t["schema"] for t in result["data"]["tables"]]
        assert "garmin_staging" not in schemas

    def test_theme(self, client: TestClient) -> None:
        result = _gql(client, "{ theme { name css } }")
        assert "errors" not in result
        assert "name" in result["data"]["theme"]

    def test_theme_with_active_theme(self, client: TestClient) -> None:
        mock_theme = MagicMock()
        mock_theme.name = "dark"
        mock_theme.css = "theme.css"
        with patch("app.server._get_active_theme", return_value=mock_theme):
            result = _gql(client, "{ theme { name css } }")
        assert result["data"]["theme"]["name"] == "dark"
        assert result["data"]["theme"]["css"] == "/themes/dark/theme.css"

    def test_theme_no_active_theme(self, client: TestClient) -> None:
        with patch("app.server._get_active_theme", return_value=None):
            result = _gql(client, "{ theme { name css } }")
        assert result["data"]["theme"]["name"] is None
        assert result["data"]["theme"]["css"] is None

    def test_hotkeys(self, client: TestClient) -> None:
        result = _gql(client, "{ hotkeys }")
        assert "errors" not in result
        data = result["data"]["hotkeys"]
        assert data["command-palette"] == "Ctrl+P"
        assert data["close-tab"] == "Ctrl+W"

    def test_workspace(self, client: TestClient) -> None:
        result = _gql(client, "{ workspace }")
        assert "errors" not in result
        assert result["data"]["workspace"] == {}

    def test_workspace_with_data(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        import json

        test_con.execute("UPDATE shenas_system.workspace SET state = ? WHERE id = 1", [json.dumps({"tabs": [1, 2]})])
        result = _gql(client, "{ workspace }")
        assert result["data"]["workspace"] == {"tabs": [1, 2]}

    def test_db_status(self, client: TestClient) -> None:
        with patch("app.api.db.db_status") as mock_status:
            from app.models import DBStatusResponse

            mock_status.return_value = DBStatusResponse(key_source="env", db_path="/tmp/test.duckdb", size_mb=1.0, schemas=[])
            result = _gql(client, "{ dbStatus { keySource dbPath sizeMb } }")
        assert "errors" not in result
        assert result["data"]["dbStatus"]["keySource"] == "env"

    def test_db_tables(self, client: TestClient) -> None:
        with patch("app.api.db.db_tables", return_value={"metrics": ["daily_hrv"]}):
            result = _gql(client, "{ dbTables }")
        assert "errors" not in result
        assert result["data"]["dbTables"] == {"metrics": ["daily_hrv"]}

    def test_schema_tables(self, client: TestClient) -> None:
        with patch("app.api.db.schema_plugin_tables", return_value={"metrics": ["daily_hrv"]}):
            result = _gql(client, "{ schemaTables }")
        assert "errors" not in result
        assert result["data"]["schemaTables"] == {"metrics": ["daily_hrv"]}

    def test_schema_plugins(self, client: TestClient) -> None:
        with patch("app.api.db.schema_plugin_ownership", return_value={"fitness": ["daily_hrv"]}):
            result = _gql(client, "{ schemaPlugins }")
        assert "errors" not in result
        assert result["data"]["schemaPlugins"] == {"fitness": ["daily_hrv"]}

    def test_transforms_empty(self, client: TestClient) -> None:
        result = _gql(client, "{ transforms { id sql enabled } }")
        assert "errors" not in result
        assert result["data"]["transforms"] == []

    def test_transforms_with_data(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql, description) "
            "VALUES ('garmin', 'activities', 'metrics', 'daily_activities', 'garmin', "
            "'SELECT 1 AS id', 'test transform')"
        )
        result = _gql(client, "{ transforms { id sourceDuckdbSchema sourcePlugin sql enabled description } }")
        assert "errors" not in result
        transforms = result["data"]["transforms"]
        assert len(transforms) == 1
        assert transforms[0]["sourcePlugin"] == "garmin"
        assert transforms[0]["sql"] == "SELECT 1 AS id"
        assert transforms[0]["enabled"] is True

    def test_transforms_filtered_by_source(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql) VALUES "
            "('garmin', 'activities', 'metrics', 'daily', 'garmin', 'SELECT 1')"
        )
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql) VALUES "
            "('lunchmoney', 'txn', 'metrics', 'spending', 'lunchmoney', 'SELECT 2')"
        )
        result = _gql(client, '{ transforms(source: "garmin") { sourcePlugin } }')
        assert "errors" not in result
        assert len(result["data"]["transforms"]) == 1
        assert result["data"]["transforms"][0]["sourcePlugin"] == "garmin"

    def test_transform_by_id(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql) VALUES "
            "('garmin', 'activities', 'metrics', 'daily', 'garmin', 'SELECT 1')"
        )
        row = test_con.execute("SELECT id FROM shenas_system.transforms LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(client, f"{{ transform(transformId: {tid}) {{ id sql enabled }} }}")
        assert "errors" not in result
        assert result["data"]["transform"]["id"] == tid
        assert result["data"]["transform"]["sql"] == "SELECT 1"

    def test_transform_by_id_not_found(self, client: TestClient) -> None:
        result = _gql(client, "{ transform(transformId: 9999) { id sql } }")
        assert "errors" not in result
        assert result["data"]["transform"] is None

    def test_plugins(self, client: TestClient) -> None:
        mock_data = [
            {
                "name": "garmin",
                "display_name": "Garmin",
                "package": "shenas-source-garmin",
                "version": "1.0.0",
                "signature": "valid",
                "enabled": True,
                "config_entries": [],
            }
        ]
        with patch("shenas_plugins.core.plugin.Plugin.list_installed", return_value=mock_data):
            result = _gql(client, '{ plugins(kind: "source") { name displayName enabled version } }')
        assert "errors" not in result
        plugins = result["data"]["plugins"]
        assert len(plugins) == 1
        assert plugins[0]["name"] == "garmin"
        assert plugins[0]["enabled"] is True

    def test_plugin_info(self, client: TestClient) -> None:
        mock_cls = MagicMock()
        mock_cls.return_value.get_info.return_value = {
            "name": "garmin",
            "kind": "source",
            "display_name": "Garmin Connect",
        }
        with patch("app.api.sources._load_plugin", return_value=mock_cls):
            result = _gql(client, '{ pluginInfo(kind: "source", name: "garmin") }')
        assert "errors" not in result
        assert result["data"]["pluginInfo"]["name"] == "garmin"

    def test_plugin_info_not_found(self, client: TestClient) -> None:
        with (
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.sources._load_plugin_fresh", return_value=None),
        ):
            result = _gql(client, '{ pluginInfo(kind: "source", name: "nonexistent") }')
        assert "errors" not in result
        info = result["data"]["pluginInfo"]
        assert info["name"] == "nonexistent"
        assert info["kind"] == "source"

    def test_device_name(self, client: TestClient) -> None:
        with patch("app.mesh.identity.get_device_info", return_value={"device_name": "my-laptop"}):
            result = _gql(client, "{ deviceName }")
        assert "errors" not in result
        assert result["data"]["deviceName"] == "my-laptop"

    def test_device_name_fallback(self, client: TestClient) -> None:
        with patch("app.mesh.identity.get_device_info", side_effect=RuntimeError("no identity")):
            result = _gql(client, "{ deviceName }")
        assert "errors" not in result
        assert result["data"]["deviceName"] == ""

    def test_dashboards(self, client: TestClient) -> None:
        mock_cls = MagicMock()
        mock_cls.name = "fitness-dashboard"
        mock_cls.display_name = "Fitness Dashboard"
        mock_cls.tag = "fitness-dashboard"
        mock_cls.entrypoint = "index.js"
        mock_cls.description = "Charts"
        mock_cls.return_value.enabled = True
        with patch("app.api.sources._load_dashboards", return_value=[mock_cls]):
            result = _gql(client, "{ dashboards }")
        assert "errors" not in result
        dashboards = result["data"]["dashboards"]
        assert len(dashboards) == 1
        assert dashboards[0]["name"] == "fitness-dashboard"
        assert dashboards[0]["js"] == "/dashboards/fitness-dashboard/index.js"

    def test_dashboards_disabled_excluded(self, client: TestClient) -> None:
        mock_cls = MagicMock()
        mock_cls.name = "fitness-dashboard"
        mock_cls.display_name = "Fitness Dashboard"
        mock_cls.tag = "fitness-dashboard"
        mock_cls.entrypoint = "index.js"
        mock_cls.description = "Charts"
        mock_cls.return_value.enabled = False
        with patch("app.api.sources._load_dashboards", return_value=[mock_cls]):
            result = _gql(client, "{ dashboards }")
        assert "errors" not in result
        assert result["data"]["dashboards"] == []

    def test_sync_schedule_empty(self, client: TestClient) -> None:
        with patch("app.api.sources._load_plugins", return_value=[]):
            result = _gql(client, "{ syncSchedule { name syncFrequency isDue } }")
        assert "errors" not in result
        assert result["data"]["syncSchedule"] == []

    def test_sync_schedule_with_data(self, client: TestClient) -> None:
        from shenas_sources.core.source import Source

        class FakeSource(Source):
            name = "garmin"
            display_name = "Garmin"

            def resources(self, client):
                return []

        with (
            patch("app.api.sources._load_plugins", return_value=[FakeSource]),
            patch.object(FakeSource, "sync_frequency", new_callable=lambda: property(lambda self: 60)),
            patch.object(FakeSource, "enabled", new_callable=lambda: property(lambda self: True)),
            patch.object(
                FakeSource,
                "state",
                new_callable=lambda: property(lambda self: {"synced_at": "2026-03-15 10:00:00", "enabled": True}),
            ),
            patch.object(FakeSource, "is_due_for_sync", new_callable=lambda: property(lambda self: True)),
        ):
            result = _gql(client, "{ syncSchedule { name syncFrequency isDue } }")
        assert "errors" not in result
        schedules = result["data"]["syncSchedule"]
        assert len(schedules) == 1
        assert schedules[0]["name"] == "garmin"
        assert schedules[0]["isDue"] is True

    def test_dependencies(self, client: TestClient) -> None:
        result = _gql(client, "{ dependencies }")
        assert "errors" not in result
        # Returns a JSON dict, possibly empty
        assert isinstance(result["data"]["dependencies"], dict)


class TestGraphQLMutations:
    def test_set_hotkey(self, client: TestClient) -> None:
        with patch("app.hotkeys.Hotkey.set"):
            result = _gql(
                client,
                'mutation { setHotkey(actionId: "test-action", binding: "Ctrl+X") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["setHotkey"]["ok"] is True

    def test_delete_hotkey(self, client: TestClient) -> None:
        with patch("app.hotkeys.Hotkey.delete"):
            result = _gql(
                client,
                'mutation { deleteHotkey(actionId: "command-palette") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["deleteHotkey"]["ok"] is True

    def test_reset_hotkeys(self, client: TestClient) -> None:
        with patch("app.hotkeys.Hotkey.reset"):
            result = _gql(client, "mutation { resetHotkeys { ok } }")
        assert "errors" not in result
        assert result["data"]["resetHotkeys"]["ok"] is True

    def test_save_workspace(self, client: TestClient) -> None:
        with patch("app.workspace.Workspace.put"):
            result = _gql(
                client,
                'mutation { saveWorkspace(data: {key: "value"}) { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["saveWorkspace"]["ok"] is True

    def test_save_workspace_with_nested_data(self, client: TestClient) -> None:
        with patch("app.workspace.Workspace.put") as mock_save:
            result = _gql(
                client,
                'mutation { saveWorkspace(data: {tabs: ["a", "b"], active: 0}) { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["saveWorkspace"]["ok"] is True
        mock_save.assert_called_once()

    def test_create_transform(self, client: TestClient) -> None:
        result = _gql(
            client,
            """mutation {
                createTransform(transformInput: {
                    sourceDuckdbSchema: "garmin",
                    sourceDuckdbTable: "activities",
                    targetDuckdbSchema: "metrics",
                    targetDuckdbTable: "daily_activities",
                    sourcePlugin: "garmin",
                    sql: "SELECT 1 AS id, 'garmin' AS source",
                    description: "test transform"
                }) { id sourceDuckdbSchema sourcePlugin sql enabled isDefault description }
            }""",
        )
        assert "errors" not in result
        t = result["data"]["createTransform"]
        assert t["sourcePlugin"] == "garmin"
        assert t["sql"] == "SELECT 1 AS id, 'garmin' AS source"
        assert t["enabled"] is True
        assert t["isDefault"] is False
        assert t["description"] == "test transform"

    def test_update_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql) VALUES "
            "('garmin', 'act', 'metrics', 'daily', 'garmin', 'SELECT 1')"
        )
        row = test_con.execute("SELECT id FROM shenas_system.transforms LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(
            client,
            f'mutation {{ updateTransform(transformId: {tid}, sql: "SELECT 2 AS new_col") {{ id sql }} }}',
        )
        assert "errors" not in result
        assert result["data"]["updateTransform"]["sql"] == "SELECT 2 AS new_col"

    def test_update_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { updateTransform(transformId: 9999, sql: "SELECT 1") { id sql } }',
        )
        assert "errors" not in result
        assert result["data"]["updateTransform"] is None

    def test_delete_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql) VALUES "
            "('garmin', 'act', 'metrics', 'daily', 'garmin', 'SELECT 1')"
        )
        row = test_con.execute("SELECT id FROM shenas_system.transforms LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(
            client,
            f"mutation {{ deleteTransform(transformId: {tid}) {{ ok }} }}",
        )
        assert "errors" not in result
        assert result["data"]["deleteTransform"]["ok"] is True

    def test_enable_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql, enabled) VALUES "
            "('garmin', 'act', 'metrics', 'daily', 'garmin', 'SELECT 1', FALSE)"
        )
        row = test_con.execute("SELECT id FROM shenas_system.transforms LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(
            client,
            f"mutation {{ enableTransform(transformId: {tid}) {{ id enabled }} }}",
        )
        assert "errors" not in result
        assert result["data"]["enableTransform"]["enabled"] is True

    def test_disable_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql) VALUES "
            "('garmin', 'act', 'metrics', 'daily', 'garmin', 'SELECT 1')"
        )
        row = test_con.execute("SELECT id FROM shenas_system.transforms LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(
            client,
            f"mutation {{ disableTransform(transformId: {tid}) {{ id enabled }} }}",
        )
        assert "errors" not in result
        assert result["data"]["disableTransform"]["enabled"] is False

    def test_enable_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            "mutation { enableTransform(transformId: 9999) { id enabled } }",
        )
        assert "errors" not in result
        assert result["data"]["enableTransform"] is None

    def test_disable_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            "mutation { disableTransform(transformId: 9999) { id enabled } }",
        )
        assert "errors" not in result
        assert result["data"]["disableTransform"] is None

    def test_enable_plugin(self, client: TestClient) -> None:
        class FakePlugin:
            def enable(self):
                return "enabled"

        with patch("app.api.sources._load_plugin", return_value=FakePlugin):
            result = _gql(
                client,
                'mutation { enablePlugin(kind: "source", name: "garmin") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["enablePlugin"]["ok"] is True

    def test_disable_plugin(self, client: TestClient) -> None:
        class FakePlugin:
            def disable(self):
                return "disabled"

        with patch("app.api.sources._load_plugin", return_value=FakePlugin):
            result = _gql(
                client,
                'mutation { disablePlugin(kind: "source", name: "garmin") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["disablePlugin"]["ok"] is True

    def test_test_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO shenas_system.transforms "
            "(source_duckdb_schema, source_duckdb_table, target_duckdb_schema, "
            "target_duckdb_table, source_plugin, sql) VALUES "
            "('garmin', 'act', 'metrics', 'daily', 'garmin', "
            "'SELECT 1 AS id, ''garmin'' AS source')"
        )
        row = test_con.execute("SELECT id FROM shenas_system.transforms LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(
            client,
            f"mutation {{ testTransform(transformId: {tid}, limit: 5) }}",
        )
        assert "errors" not in result
        rows = result["data"]["testTransform"]
        assert len(rows) == 1
        assert rows[0]["id"] == 1
        assert rows[0]["source"] == "garmin"

    def test_test_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            "mutation { testTransform(transformId: 9999) }",
        )
        assert "errors" not in result
        assert result["data"]["testTransform"] == []

    def test_config_value_query(self, client: TestClient) -> None:
        class FakePlugin:
            def get_config_value(self, key):
                return "2024-01-01" if key == "start_date" else None

        with patch("app.api.sources._load_plugin", return_value=FakePlugin):
            result = _gql(client, '{ configValue(kind: "source", name: "garmin", key: "start_date") }')
        assert "errors" not in result
        assert result["data"]["configValue"] == "2024-01-01"

    def test_config_value_query_not_found(self, client: TestClient) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            result = _gql(client, '{ configValue(kind: "source", name: "garmin", key: "missing") }')
        assert "errors" not in result
        assert result["data"]["configValue"] is None


class TestGraphQLMutationsExtra:
    """Coverage for mutations that aren't covered above."""

    def test_authenticate(self, client: TestClient) -> None:
        fake_source = MagicMock()
        fake_source.handle_auth.return_value = {"ok": True, "needs_mfa": False, "auth_url": None, "message": "logged in"}
        with patch("app.api.sources._load_source", return_value=fake_source):
            result = _gql(
                client,
                'mutation { authenticate(pipe: "garmin", credentials: {username: "u", password: "p"}) { ok message } }',
            )
        assert "errors" not in result
        assert result["data"]["authenticate"]["ok"] is True
        assert result["data"]["authenticate"]["message"] == "logged in"
        fake_source.handle_auth.assert_called_once()

    def test_set_config_success(self, client: TestClient) -> None:
        fake_plugin = MagicMock()
        fake_cls = MagicMock(return_value=fake_plugin)
        with patch("app.api.sources._load_plugin", return_value=fake_cls):
            result = _gql(
                client,
                'mutation { setConfig(kind: "source", name: "garmin", key: "k", value: "v") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["setConfig"]["ok"] is True
        fake_plugin.set_config_value.assert_called_once_with("k", "v")

    def test_set_config_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            result = _gql(
                client,
                'mutation { setConfig(kind: "source", name: "missing", key: "k", value: "v") { ok message } }',
            )
        assert result["data"]["setConfig"]["ok"] is False
        assert "missing" in result["data"]["setConfig"]["message"]

    def test_delete_config_success(self, client: TestClient) -> None:
        fake_plugin = MagicMock()
        fake_cls = MagicMock(return_value=fake_plugin)
        with patch("app.api.sources._load_plugin", return_value=fake_cls):
            result = _gql(client, 'mutation { deleteConfig(kind: "source", name: "garmin") { ok } }')
        assert result["data"]["deleteConfig"]["ok"] is True
        fake_plugin.delete_config.assert_called_once()

    def test_delete_config_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            result = _gql(client, 'mutation { deleteConfig(kind: "source", name: "missing") { ok message } }')
        assert result["data"]["deleteConfig"]["ok"] is False

    def test_delete_config_key_success(self, client: TestClient) -> None:
        fake_plugin = MagicMock()
        fake_cls = MagicMock(return_value=fake_plugin)
        with patch("app.api.sources._load_plugin", return_value=fake_cls):
            result = _gql(
                client,
                'mutation { deleteConfigKey(kind: "source", name: "garmin", key: "k") { ok } }',
            )
        assert result["data"]["deleteConfigKey"]["ok"] is True
        fake_plugin.set_config_value.assert_called_once_with("k", None)

    def test_delete_config_key_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            result = _gql(
                client,
                'mutation { deleteConfigKey(kind: "source", name: "missing", key: "k") { ok message } }',
            )
        assert result["data"]["deleteConfigKey"]["ok"] is False

    def test_generate_db_key(self, client: TestClient) -> None:
        with patch("app.db.generate_db_key", return_value="newkey"), patch("app.db.set_db_key") as mock_set:
            result = _gql(client, "mutation { generateDbKey { ok } }")
        assert result["data"]["generateDbKey"]["ok"] is True
        mock_set.assert_called_once_with("newkey")

    def test_flush_schema(self, client: TestClient) -> None:
        with patch("app.api.db.flush_schema", return_value={"flushed": "metrics", "rows_deleted": 10}):
            result = _gql(
                client,
                'mutation { flushSchema(schemaPlugin: "fitness") }',
            )
        assert "errors" not in result
        assert result["data"]["flushSchema"]["flushed"] == "metrics"

    def test_install_plugins(self, client: TestClient) -> None:
        with patch("shenas_plugins.core.plugin.Plugin.install", return_value=(True, "installed")):
            result = _gql(
                client,
                'mutation { installPlugins(kind: "source", names: ["garmin", "spotify"], skipVerify: true) '
                "{ results { name ok message } } }",
            )
        assert "errors" not in result
        results = result["data"]["installPlugins"]["results"]
        assert len(results) == 2
        assert all(r["ok"] for r in results)

    def test_remove_plugin(self, client: TestClient) -> None:
        with patch("shenas_plugins.core.plugin.Plugin.uninstall", return_value=(True, "removed")):
            result = _gql(
                client,
                'mutation { removePlugin(kind: "source", name: "garmin") { ok message } }',
            )
        assert result["data"]["removePlugin"]["ok"] is True
        assert result["data"]["removePlugin"]["message"] == "removed"

    def test_enable_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            result = _gql(
                client,
                'mutation { enablePlugin(kind: "source", name: "missing") { ok message } }',
            )
        assert result["data"]["enablePlugin"]["ok"] is False

    def test_disable_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            result = _gql(
                client,
                'mutation { disablePlugin(kind: "source", name: "missing") { ok message } }',
            )
        assert result["data"]["disablePlugin"]["ok"] is False

    def test_seed_transforms(self, client: TestClient) -> None:
        fake_ep = MagicMock()
        fake_ep.name = "garmin"
        with (
            patch("importlib.metadata.entry_points", return_value=[fake_ep]),
            patch("shenas_sources.core.transform.load_transform_defaults", return_value=[{"sql": "SELECT 1"}]),
            patch("app.transforms.Transform.seed_defaults") as mock_seed,
        ):
            result = _gql(client, "mutation { seedTransforms }")
        assert "errors" not in result
        assert result["data"]["seedTransforms"]["count"] == 1
        assert result["data"]["seedTransforms"]["seeded"] == ["garmin"]
        mock_seed.assert_called_once()

    def test_seed_transforms_no_defaults(self, client: TestClient) -> None:
        fake_ep = MagicMock()
        fake_ep.name = "duolingo"
        with (
            patch("importlib.metadata.entry_points", return_value=[fake_ep]),
            patch("shenas_sources.core.transform.load_transform_defaults", return_value=[]),
        ):
            result = _gql(client, "mutation { seedTransforms }")
        assert result["data"]["seedTransforms"]["count"] == 0

    def test_run_pipe_transforms(self, client: TestClient) -> None:
        with patch("app.transforms.Transform.run_for_source", return_value=3):
            result = _gql(client, 'mutation { runPipeTransforms(pipe: "garmin") }')
        assert "errors" not in result
        assert result["data"]["runPipeTransforms"]["source"] == "garmin"
        assert result["data"]["runPipeTransforms"]["count"] == 3

    def test_run_schema_transforms(self, client: TestClient) -> None:
        with patch("app.transforms.Transform.run_for_target", return_value=2):
            result = _gql(client, 'mutation { runSchemaTransforms(schema: "metrics") }')
        assert "errors" not in result
        assert result["data"]["runSchemaTransforms"]["schema"] == "metrics"
        assert result["data"]["runSchemaTransforms"]["count"] == 2
