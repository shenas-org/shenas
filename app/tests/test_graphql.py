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

    @pytest.mark.skip(reason="Transform DB isolation")
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

    @pytest.mark.skip(reason="Transform DB isolation")
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

    @pytest.mark.skip(reason="Transform DB isolation")
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

    @pytest.mark.skip(reason="Transform DB isolation")
    def test_transform_by_id_not_found(self, client: TestClient) -> None:
        result = _gql(client, "{ transform(transformId: 9999) { id sql } }")
        assert "errors" not in result
        assert result["data"]["transform"] is None

    def test_plugins(self, client: TestClient) -> None:
        from app.models import PluginInfo

        mock_info = PluginInfo(
            name="garmin",
            display_name="Garmin",
            package="shenas-source-garmin",
            version="1.0.0",
            signature="valid",
            enabled=True,
        )
        with patch("app.api.plugins.list_plugins_data", return_value=[mock_info]):
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

    def test_components(self, client: TestClient) -> None:
        mock_component = MagicMock()
        mock_component.name = "fitness-dashboard"
        mock_component.display_name = "Fitness Dashboard"
        mock_component.tag = "fitness-dashboard"
        mock_component.entrypoint = "index.js"
        mock_component.description = "Charts"
        with (
            patch("app.api.sources._load_dashboards", return_value=[mock_component]),
            patch("app.db.is_plugin_enabled", return_value=True),
        ):
            result = _gql(client, "{ components }")
        assert "errors" not in result
        components = result["data"]["components"]
        assert len(components) == 1
        assert components[0]["name"] == "fitness-dashboard"
        assert components[0]["js"] == "/components/fitness-dashboard/index.js"

    def test_components_disabled_excluded(self, client: TestClient) -> None:
        mock_component = MagicMock()
        mock_component.name = "fitness-dashboard"
        mock_component.display_name = "Fitness Dashboard"
        mock_component.tag = "fitness-dashboard"
        mock_component.entrypoint = "index.js"
        mock_component.description = "Charts"
        with (
            patch("app.api.sources._load_dashboards", return_value=[mock_component]),
            patch("app.db.is_plugin_enabled", return_value=False),
        ):
            result = _gql(client, "{ components }")
        assert "errors" not in result
        assert result["data"]["components"] == []

    def test_sync_schedule_empty(self, client: TestClient) -> None:
        with patch("app.db.get_all_sync_schedules", return_value=[]):
            result = _gql(client, "{ syncSchedule { name syncFrequency isDue } }")
        assert "errors" not in result
        assert result["data"]["syncSchedule"] == []

    def test_sync_schedule_with_data(self, client: TestClient) -> None:
        with patch(
            "app.db.get_all_sync_schedules",
            return_value=[{"name": "garmin", "synced_at": "2026-03-15 10:00:00", "sync_frequency": 60, "is_due": True}],
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
        with patch("app.db.set_hotkey"):
            result = _gql(
                client,
                'mutation { setHotkey(actionId: "test-action", binding: "Ctrl+X") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["setHotkey"]["ok"] is True

    def test_delete_hotkey(self, client: TestClient) -> None:
        with patch("app.db.set_hotkey") as mock_set:
            result = _gql(
                client,
                'mutation { deleteHotkey(actionId: "command-palette") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["deleteHotkey"]["ok"] is True
        mock_set.assert_called_once_with("command-palette", "")

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

    def test_save_workspace_with_nested_data(self, client: TestClient) -> None:
        with patch("app.db.save_workspace") as mock_save:
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

    @pytest.mark.skip(reason="Transform DB isolation")
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

    @pytest.mark.skip(reason="Transform DB isolation")
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

    @pytest.mark.skip(reason="Transform DB isolation")
    def test_enable_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            "mutation { enableTransform(transformId: 9999) { id enabled } }",
        )
        assert "errors" not in result
        assert result["data"]["enableTransform"] is None

    @pytest.mark.skip(reason="Transform DB isolation")
    def test_disable_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            "mutation { disableTransform(transformId: 9999) { id enabled } }",
        )
        assert "errors" not in result
        assert result["data"]["disableTransform"] is None

    def test_enable_plugin(self, client: TestClient) -> None:
        from app.models import OkResponse

        with patch("app.api.plugins.enable_plugin", return_value=OkResponse(ok=True, message="enabled")):
            result = _gql(
                client,
                'mutation { enablePlugin(kind: "source", name: "garmin") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["enablePlugin"]["ok"] is True

    def test_disable_plugin(self, client: TestClient) -> None:
        from app.models import OkResponse

        with patch("app.api.plugins.disable_plugin", return_value=OkResponse(ok=True, message="disabled")):
            result = _gql(
                client,
                'mutation { disablePlugin(kind: "source", name: "garmin") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["disablePlugin"]["ok"] is True

    @pytest.mark.skip(reason="Transform DB isolation")
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

    @pytest.mark.skip(reason="Transform DB isolation")
    def test_test_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            "mutation { testTransform(transformId: 9999) }",
        )
        assert "errors" not in result
        assert result["data"]["testTransform"] == []

    def test_config_query(self, client: TestClient) -> None:
        from app.models import ConfigEntry, ConfigItem

        mock_items = [
            ConfigItem(
                kind="source",
                name="garmin",
                entries=[ConfigEntry(key="start_date", label="Start Date", value="2024-01-01", description="")],
            )
        ]
        with patch("app.api.config.list_configs", return_value=mock_items):
            result = _gql(client, '{ config(kind: "source") { kind name entries { key value } } }')
        assert "errors" not in result
        configs = result["data"]["config"]
        assert len(configs) == 1
        assert configs[0]["name"] == "garmin"
        assert configs[0]["entries"][0]["key"] == "start_date"

    def test_config_value_query(self, client: TestClient) -> None:
        from app.models import ConfigValueResponse

        mock_resp = ConfigValueResponse(key="start_date", value="2024-01-01")
        with patch("app.api.config.get_config_value", return_value=mock_resp):
            result = _gql(client, '{ configValue(kind: "source", name: "garmin", key: "start_date") }')
        assert "errors" not in result
        assert result["data"]["configValue"] == "2024-01-01"

    def test_config_value_query_not_found(self, client: TestClient) -> None:
        with patch("app.api.config.get_config_value", side_effect=Exception("Not set")):
            result = _gql(client, '{ configValue(kind: "source", name: "garmin", key: "missing") }')
        assert "errors" not in result
        assert result["data"]["configValue"] is None
