"""Tests for the GraphQL endpoint."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Annotated, ClassVar  # noqa: F401 - used in test class annotations
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

import duckdb
import pytest

# Ensure hypothesis mode is registered for all tests that need it.
import shenas_analyses.hypothesis  # noqa: F401
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """In-memory DuckDB with test data, attached as 'db' like the real server."""
    import app.database
    import app.db

    con = duckdb.connect()
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA metrics")
    con.execute("CREATE TABLE metrics.daily_hrv (date DATE, source VARCHAR, rmssd DOUBLE)")
    con.execute("INSERT INTO metrics.daily_hrv VALUES ('2026-03-15', 'garmin', 42.0)")
    con.execute("CREATE SCHEMA garmin")
    con.execute("CREATE TABLE garmin.activities (id INTEGER, start_time_local DATE)")
    con.execute("INSERT INTO garmin.activities VALUES (1, '2026-03-15')")

    @contextlib.contextmanager
    def _cursor(**_kwargs: object) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        cur = con.cursor()
        cur.execute("USE db")
        try:
            yield cur
        finally:
            cur.close()

    class _StubDB:
        def cursor(self) -> contextlib.AbstractContextManager:
            return _cursor()

        def connect(self) -> duckdb.DuckDBPyConnection:
            return con

        def close(self) -> None:
            pass

    stub = _StubDB()
    saved = dict(app.db._resolvers)
    app.db._resolvers["shenas"] = lambda: stub  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    app.db._resolvers[None] = lambda: stub  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    app.database._ensure_system_tables(con)
    con.execute("INSERT INTO ui.workspace (id, state) VALUES (1, '{}')")
    yield con
    app.db._resolvers.clear()
    app.db._resolvers.update(saved)
    con.close()


@pytest.fixture
def client(test_con: duckdb.DuckDBPyConnection) -> Iterator[TestClient]:
    import app.database as _database

    with (
        patch("app.database.connect", return_value=test_con),
        patch("app.api.query.cursor", side_effect=_database.cursor),
        patch("app.api.db.cursor", side_effect=_database.cursor),
    ):
        yield TestClient(app)


def _gql(client: TestClient, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query and return the parsed response."""
    resp = client.post("/api/graphql", json={"query": query, "variables": variables or {}})
    assert resp.status_code == 200
    return resp.json()


# Module-scope test fixture for catalog tests. Defined here (rather than
# inside the test function) so `get_type_hints` can resolve `Annotated`
# and `Field` from this module's namespace.
from app.schema import METRICS  # noqa: E402
from app.table import Field  # noqa: E402
from shenas_datasets.core import DailyMetricTable  # noqa: E402


class _CatalogMood(DailyMetricTable):
    class _Meta:
        name = "daily_mood_test"
        display_name = "Daily Mood (test)"
        description = "Test metric."
        schema = METRICS
        pk = ("date", "source")

    date: Annotated[str, Field(db_type="DATE", description="Calendar date")] = ""
    source: Annotated[str, Field(db_type="VARCHAR", description="Source")] = ""
    mood: Annotated[float | None, Field(db_type="DOUBLE", description="Mood 1-10")] = None


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
        with patch("app.main._get_active_theme", return_value=mock_theme):
            result = _gql(client, "{ theme { name css } }")
        assert result["data"]["theme"]["name"] == "dark"
        assert result["data"]["theme"]["css"] == "/themes/dark/theme.css"

    def test_theme_no_active_theme(self, client: TestClient) -> None:
        with patch("app.main._get_active_theme", return_value=None):
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

        test_con.execute(
            "UPDATE ui.workspace SET state = ? WHERE id = 1",
            [json.dumps({"tabs": [1, 2]})],
        )
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
        result = _gql(client, "{ transforms { id transformType enabled } }")
        assert "errors" not in result
        assert result["data"]["transforms"] == []

    def test_transforms_with_data(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params, description) "
            "VALUES ('sql', 'garmin.activities', 'metrics.daily_activities', 'garmin', "
            "'{\"sql\": \"SELECT 1 AS id\"}', 'test transform')"
        )
        result = _gql(
            client,
            "{ transforms { id transformType sourcePlugin params enabled description } }",
        )
        assert "errors" not in result
        transforms = result["data"]["transforms"]
        assert len(transforms) == 1
        assert transforms[0]["sourcePlugin"] == "garmin"
        assert transforms[0]["transformType"] == "sql"
        assert transforms[0]["enabled"] is True

    def test_transforms_filtered_by_source(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params) VALUES "
            "('sql', 'garmin.activities', 'metrics.daily', 'garmin', '{\"sql\": \"SELECT 1\"}')"
        )
        test_con.execute(
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params) VALUES "
            "('sql', 'lunchmoney.txn', 'metrics.spending', 'lunchmoney', '{\"sql\": \"SELECT 2\"}')"
        )
        result = _gql(client, '{ transforms(source: "garmin") { sourcePlugin } }')
        assert "errors" not in result
        assert len(result["data"]["transforms"]) == 1
        assert result["data"]["transforms"][0]["sourcePlugin"] == "garmin"

    def test_transform_by_id(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params) VALUES "
            "('sql', 'garmin.activities', 'metrics.daily', 'garmin', '{\"sql\": \"SELECT 1\"}')"
        )
        row = test_con.execute("SELECT id FROM transforms.instances LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(client, f"{{ transform(transformId: {tid}) {{ id transformType enabled }} }}")
        assert "errors" not in result
        assert result["data"]["transform"]["id"] == tid
        assert result["data"]["transform"]["transformType"] == "sql"

    def test_transform_by_id_not_found(self, client: TestClient) -> None:
        result = _gql(client, "{ transform(transformId: 9999) { id transformType } }")
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
        with patch("app.plugin.Plugin.list_installed", return_value=mock_data):
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
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=mock_cls):
            result = _gql(client, '{ pluginInfo(kind: "source", name: "garmin") }')
        assert "errors" not in result
        assert result["data"]["pluginInfo"]["name"] == "garmin"

    def test_plugin_info_not_found(self, client: TestClient) -> None:
        with (
            patch("app.plugin.Plugin.load_by_name_and_kind", return_value=None),
            patch("app.plugin.Plugin._load_fresh", return_value=None),
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
        mock_cls.name = "fitness"
        mock_cls.display_name = "Fitness Dashboard"
        mock_cls.tag = "fitness"
        mock_cls.entrypoint = "index.js"
        mock_cls.description = "Charts"
        mock_cls.return_value.enabled = True
        with patch("shenas_dashboards.core.Dashboard.load_all", return_value=[mock_cls]):
            result = _gql(client, "{ dashboards { name displayName tag js description } }")
        assert "errors" not in result
        dashboards = result["data"]["dashboards"]
        assert len(dashboards) == 1
        assert dashboards[0]["name"] == "fitness"
        assert dashboards[0]["js"] == "/dashboards/fitness/index.js"

    def test_dashboards_disabled_excluded(self, client: TestClient) -> None:
        mock_cls = MagicMock()
        mock_cls.name = "fitness"
        mock_cls.display_name = "Fitness Dashboard"
        mock_cls.tag = "fitness"
        mock_cls.entrypoint = "index.js"
        mock_cls.description = "Charts"

        class _DisabledInstance:
            enabled = False

        with (
            patch("shenas_dashboards.core.Dashboard.load_all", return_value=[mock_cls]),
            patch("app.plugin.PluginInstance.find", return_value=_DisabledInstance()),
        ):
            result = _gql(client, "{ dashboards { name displayName tag js description } }")
        assert "errors" not in result
        assert result["data"]["dashboards"] == []

    def test_sync_schedule_empty(self, client: TestClient) -> None:
        with patch("shenas_sources.core.source.Source.load_all", return_value=[]):
            result = _gql(client, "{ syncSchedule { name syncFrequency isDue } }")
        assert "errors" not in result
        assert result["data"]["syncSchedule"] == []

    def test_catalog_empty_when_no_plugins(self, client: TestClient) -> None:
        with (
            patch("app.plugin.Plugin.load_by_kind", return_value=[]),
            patch("shenas_datasets.core.dataset.Dataset.load_all", return_value=[]),
        ):
            result = _gql(client, "{ catalog { id displayName kind } }")
        assert "errors" not in result
        assert result["data"]["catalog"] == []

    def test_catalog_returns_dataset_metadata(self, client: TestClient) -> None:
        fake_dataset = MagicMock()
        fake_dataset.name = "test-dataset"
        fake_dataset.display_name = "Test Dataset"
        fake_dataset.description = ""
        fake_dataset.all_tables = [_CatalogMood]
        fake_dataset.return_value = fake_dataset
        with (
            patch("app.plugin.Plugin.load_by_kind", return_value=[]),
            patch("shenas_datasets.core.dataset.Dataset.load_all", return_value=[fake_dataset]),
        ):
            result = _gql(client, "{ catalog { id displayName kind } }")
        assert "errors" not in result
        catalog = result["data"]["catalog"]
        assert len(catalog) == 1
        entry = catalog[0]
        assert entry["id"] == "metrics.daily_mood_test"
        assert entry["kind"] == "daily_metric"

    def test_sync_schedule_with_data(self, client: TestClient) -> None:
        from shenas_sources.core.source import Source

        class FakeSource(Source):
            name = "garmin"
            display_name = "Garmin"

            def resources(self, client):
                return []

        class _FakeInstance:
            enabled = True
            synced_at = "2026-03-15 10:00:00"

        with (
            patch("shenas_sources.core.source.Source.load_all", return_value=[FakeSource]),
            patch.object(FakeSource, "sync_frequency", new_callable=lambda: property(lambda self: 60)),
            patch.object(FakeSource, "instance", return_value=_FakeInstance()),
            patch.object(FakeSource, "is_due_for_sync", new_callable=lambda: property(lambda self: True)),
        ):
            result = _gql(client, "{ syncSchedule { name syncFrequency isDue } }")
        assert "errors" not in result
        schedules = result["data"]["syncSchedule"]
        assert len(schedules) == 1
        assert schedules[0]["name"] == "garmin"
        assert schedules[0]["isDue"] is True

    def test_dependencies(self, client: TestClient) -> None:
        result = _gql(client, "{ dependencies { source targets } }")
        assert "errors" not in result
        # Returns a JSON dict, possibly empty
        assert isinstance(result["data"]["dependencies"], list)


class TestGraphQLMutations:
    def test_set_hotkey(self, client: TestClient) -> None:
        with patch("app.hotkeys.Hotkey.set_binding"):
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
        with patch("app.workspace.Workspace.write_row"):
            result = _gql(
                client,
                'mutation { saveWorkspace(data: {key: "value"}) { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["saveWorkspace"]["ok"] is True

    def test_save_workspace_with_nested_data(self, client: TestClient) -> None:
        with patch("app.workspace.Workspace.write_row") as mock_save:
            result = _gql(
                client,
                'mutation { saveWorkspace(data: {tabs: ["a", "b"], active: 0}) { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["saveWorkspace"]["ok"] is True
        mock_save.assert_called_once()

    # -- Analysis modes --

    def test_analysis_modes_query(self, client: TestClient) -> None:
        result = _gql(client, "{ analysisModes }")
        assert "errors" not in result
        modes = result["data"]["analysisModes"]
        assert isinstance(modes, list)
        names = [m["name"] for m in modes]
        assert "hypothesis" in names
        hyp = next(m for m in modes if m["name"] == "hypothesis")
        assert hyp["display_name"] == "Hypothesis Testing"
        assert len(hyp["description"]) > 0

    # -- Hypotheses --

    def test_create_hypothesis(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { createHypothesis(question: "does coffee affect mood?", plan: "join then correlate") }',
        )
        assert "errors" not in result
        data = result["data"]["createHypothesis"]
        assert data["question"] == "does coffee affect mood?"
        assert data["id"] >= 1
        assert data["mode"] == "hypothesis"

    def test_create_hypothesis_with_mode(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { createHypothesis(question: "q", mode: "hypothesis") }',
        )
        assert "errors" not in result
        data = result["data"]["createHypothesis"]
        assert data["mode"] == "hypothesis"

    def test_list_and_get_hypothesis(self, client: TestClient) -> None:
        created = _gql(client, 'mutation { createHypothesis(question: "q1") }')["data"]["createHypothesis"]
        hid = created["id"]

        listed = _gql(client, "{ hypotheses { id question mode } }")
        assert "errors" not in listed
        rows = listed["data"]["hypotheses"]
        assert any(r["id"] == hid and r["question"] == "q1" for r in rows)

        single = _gql(client, f"{{ hypothesis(hypothesisId: {hid}) {{ question mode resultJson }} }}")
        assert "errors" not in single
        assert single["data"]["hypothesis"]["question"] == "q1"
        assert single["data"]["hypothesis"]["mode"] == "hypothesis"
        assert not single["data"]["hypothesis"]["resultJson"]

    def test_run_recipe_attaches_result(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute("DROP TABLE IF EXISTS metrics.daily_intake")
        test_con.execute("CREATE TABLE metrics.daily_intake (date DATE, source VARCHAR, caffeine_mg DOUBLE)")
        test_con.execute(
            "INSERT INTO metrics.daily_intake VALUES "
            "('2026-01-01', 'manual', 100), ('2026-01-02', 'manual', 200), ('2026-01-03', 'manual', 0)"
        )

        created = _gql(client, 'mutation { createHypothesis(question: "what is mean caffeine?") }')
        hid = created["data"]["createHypothesis"]["id"]

        # Mock _build_catalog so this test doesn't depend on every installed
        # plugin loading cleanly under get_type_hints. The runner only
        # consults the catalog for kind / time-axis hints.
        fake_catalog = {
            "metrics.daily_intake": {
                "table": "daily_intake",
                "schema": "metrics",
                "primary_key": ["date", "source"],
                "kind": "daily_metric",
                "columns": [
                    {"name": "date", "db_type": "DATE"},
                    {"name": "source", "db_type": "VARCHAR"},
                    {"name": "caffeine_mg", "db_type": "DOUBLE"},
                ],
            }
        }
        recipe_json = ('{"nodes": {"a": {"type": "source", "table": "metrics.daily_intake"}}, "final": "a"}').replace(
            '"', '\\"'
        )
        with patch("app.graphql.mutations._build_catalog", return_value=fake_catalog):
            result = _gql(
                client,
                f'mutation {{ runRecipe(hypothesisId: {hid}, recipeJson: "{recipe_json}") }}',
            )
        assert "errors" not in result
        body = result["data"]["runRecipe"]
        assert body["id"] == hid
        assert "result" in body
        assert body["result"] is not None

    def test_run_recipe_missing_hypothesis(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { runRecipe(hypothesisId: 999999, recipeJson: "{}") }',
        )
        assert "errors" not in result
        assert "error" in result["data"]["runRecipe"]

    # -- LLM-driven hypothesis --

    def test_ask_hypothesis_with_fake_provider(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        from shenas_analyses.core.analytics import FakeProvider

        test_con.execute("DROP TABLE IF EXISTS metrics.daily_intake")
        test_con.execute("CREATE TABLE metrics.daily_intake (date DATE, source VARCHAR, caffeine_mg DOUBLE)")
        test_con.execute(
            "INSERT INTO metrics.daily_intake VALUES ('2026-01-01', 'manual', 100), ('2026-01-02', 'manual', 200)"
        )

        canned = {
            "plan": "Read daily caffeine intake.",
            "nodes": {"a": {"type": "source", "table": "metrics.daily_intake"}},
            "final": "a",
        }
        fake_catalog = {
            "metrics.daily_intake": {
                "table": "daily_intake",
                "schema": "metrics",
                "primary_key": ["date", "source"],
                "kind": "daily_metric",
                "columns": [
                    {"name": "date", "db_type": "DATE"},
                    {"name": "source", "db_type": "VARCHAR"},
                    {"name": "caffeine_mg", "db_type": "DOUBLE"},
                ],
            }
        }
        with (
            patch("app.llm.get_llm_provider", return_value=FakeProvider(canned)),
            patch("app.graphql.mutations._build_catalog", return_value=fake_catalog),
        ):
            result = _gql(
                client,
                'mutation { askHypothesis(question: "what does my caffeine look like?") }',
            )
        assert "errors" not in result
        body = result["data"]["askHypothesis"]
        assert body["plan"] == "Read daily caffeine intake."
        assert body["recipe"] == canned
        assert body["result"] is not None
        assert body["id"] >= 1

    def test_ask_hypothesis_records_cost_and_latency(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        from shenas_analyses.core.analytics import FakeProvider

        test_con.execute("DROP TABLE IF EXISTS metrics.daily_intake")
        test_con.execute("CREATE TABLE metrics.daily_intake (date DATE, source VARCHAR, x DOUBLE)")
        test_con.execute("INSERT INTO metrics.daily_intake VALUES ('2026-01-01', 'm', 1)")
        canned = {
            "plan": "p",
            "nodes": {"a": {"type": "source", "table": "metrics.daily_intake"}},
            "final": "a",
        }
        catalog = {
            "metrics.daily_intake": {
                "table": "daily_intake",
                "schema": "metrics",
                "primary_key": ["date", "source"],
                "kind": "daily_metric",
                "columns": [
                    {"name": "date", "db_type": "DATE"},
                    {"name": "source", "db_type": "VARCHAR"},
                    {"name": "x", "db_type": "DOUBLE"},
                ],
            }
        }
        provider = FakeProvider(canned, input_tokens=123, output_tokens=45)
        with (
            patch("app.llm.get_llm_provider", return_value=provider),
            patch("app.graphql.mutations._build_catalog", return_value=catalog),
        ):
            result = _gql(client, 'mutation { askHypothesis(question: "q") }')
        assert "errors" not in result
        cost = result["data"]["askHypothesis"]["cost"]
        assert cost["llm_input_tokens"] == 123
        assert cost["llm_output_tokens"] == 45
        assert cost["llm_elapsed_ms"] >= 0
        assert cost["query_elapsed_ms"] >= 0
        assert cost["wall_clock_ms"] >= 0

    # -- Forking --

    def test_fork_hypothesis(self, client: TestClient) -> None:
        from shenas_analyses.core.analytics import Recipe, SourceRef

        from app.hypotheses import Hypothesis

        recipe = Recipe(nodes={"a": SourceRef(table="metrics.daily_intake")}, final="a")
        parent = Hypothesis.create("does coffee affect mood?", recipe, plan="initial plan")

        result = _gql(client, f"mutation {{ forkHypothesis(hypothesisId: {parent.id}) }}")
        assert "errors" not in result
        body = result["data"]["forkHypothesis"]
        assert body["parent_id"] == parent.id
        assert body["question"] == parent.question
        assert body["id"] != parent.id

        fork = Hypothesis.find(body["id"])
        assert fork is not None
        assert fork.parent_id == parent.id
        assert fork.recipe_json == parent.recipe_json

    def test_fork_hypothesis_not_found(self, client: TestClient) -> None:
        result = _gql(client, "mutation { forkHypothesis(hypothesisId: 999999) }")
        assert "errors" not in result
        assert "error" in result["data"]["forkHypothesis"]

    # -- Promotion --

    def test_promote_hypothesis(self, client: TestClient) -> None:
        from shenas_analyses.core.analytics import Recipe, SourceRef

        from app.hypotheses import Hypothesis
        from shenas_datasets.promoted import PromotedMetric

        recipe = Recipe(
            nodes={"a": SourceRef(table="metrics.daily_intake")},
            final="a",
        )
        h = Hypothesis.create("q", recipe)

        result = _gql(
            client,
            f'mutation {{ promoteHypothesis(hypothesisId: {h.id}, name: "my_metric") }}',
        )
        assert "errors" not in result
        body = result["data"]["promoteHypothesis"]
        assert body["promoted_to"] == "metrics.my_metric"
        # Row landed in analysis.promoted_metrics
        row = PromotedMetric.find("my_metric", "metrics")
        assert row is not None
        assert row.hypothesis_id == h.id

    def test_promote_hypothesis_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { promoteHypothesis(hypothesisId: 999999, name: "x") }',
        )
        assert "errors" not in result
        assert "error" in result["data"]["promoteHypothesis"]

    def test_ask_hypothesis_unknown_mode_returns_error(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { askHypothesis(question: "q", mode: "nonexistent") }',
        )
        assert "errors" not in result
        body = result["data"]["askHypothesis"]
        assert body["ok"] is False
        assert "unknown analysis mode" in body["error"]["message"]

    def test_ask_hypothesis_llm_failure_persists_error(self, client: TestClient) -> None:
        class _BoomProvider:
            name = "boom@v0"

            def ask(self, **_):
                raise RuntimeError("rate limited")

        with (
            patch("app.llm.get_llm_provider", return_value=_BoomProvider()),
            patch("app.graphql.mutations._build_catalog", return_value={}),
        ):
            result = _gql(
                client,
                'mutation { askHypothesis(question: "anything") }',
            )
        assert "errors" not in result
        body = result["data"]["askHypothesis"]
        assert body["ok"] is False
        assert "rate limited" in body["error"]["message"]

    def test_create_transform(self, client: TestClient) -> None:
        result = _gql(
            client,
            """mutation {
                createTransform(transformInput: {
                    transformType: "sql",
                    sourceDuckdbSchema: "garmin",
                    sourceDuckdbTable: "activities",
                    targetDuckdbSchema: "metrics",
                    targetDuckdbTable: "daily_activities",
                    sourcePlugin: "garmin",
                    params: "{\\"sql\\": \\"SELECT 1 AS id, 'garmin' AS source\\"}",
                    description: "test transform"
                }) { id transformType sourcePlugin params enabled isDefault description }
            }""",
        )
        assert "errors" not in result
        t = result["data"]["createTransform"]
        assert t["sourcePlugin"] == "garmin"
        assert t["transformType"] == "sql"
        assert t["enabled"] is True
        assert t["isDefault"] is False
        assert t["description"] == "test transform"

    def test_update_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params) VALUES "
            "('sql', 'garmin.act', 'metrics.daily', 'garmin', '{\"sql\": \"SELECT 1\"}')"
        )
        row = test_con.execute("SELECT id FROM transforms.instances LIMIT 1").fetchone()
        assert row is not None
        tid = row[0]
        result = _gql(
            client,
            "mutation($id: Int!, $params: String!) { updateTransform(transformId: $id, params: $params) { id params } }",
            {"id": tid, "params": '{"sql": "SELECT 2 AS new_col"}'},
        )
        assert "errors" not in result
        assert result["data"]["updateTransform"] is not None

    def test_update_transform_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { updateTransform(transformId: 9999, params: "{}") { id } }',
        )
        assert "errors" not in result
        assert result["data"]["updateTransform"] is None

    def test_delete_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params) VALUES "
            "('sql', 'garmin.act', 'metrics.daily', 'garmin', '{}')"
        )
        row = test_con.execute("SELECT id FROM transforms.instances LIMIT 1").fetchone()
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
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params, enabled) VALUES "
            "('sql', 'garmin.act', 'metrics.daily', 'garmin', '{}', FALSE)"
        )
        row = test_con.execute("SELECT id FROM transforms.instances LIMIT 1").fetchone()
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
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params) VALUES "
            "('sql', 'garmin.act', 'metrics.daily', 'garmin', '{}')"
        )
        row = test_con.execute("SELECT id FROM transforms.instances LIMIT 1").fetchone()
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
        result = _gql(
            client,
            'mutation { enablePlugin(kind: "source", name: "garmin") { ok } }',
        )
        assert "errors" not in result
        assert result["data"]["enablePlugin"]["ok"] is True

    def test_disable_plugin(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        # Ensure the PluginInstance row exists so disable can find it.
        test_con.execute("INSERT INTO plugins.installed (kind, name, enabled) VALUES ('source', 'garmin', TRUE)")
        result = _gql(
            client,
            'mutation { disablePlugin(kind: "source", name: "garmin") { ok } }',
        )
        assert "errors" not in result
        assert result["data"]["disablePlugin"]["ok"] is True

    def test_test_transform(self, client: TestClient, test_con: duckdb.DuckDBPyConnection) -> None:
        test_con.execute(
            "INSERT INTO transforms.instances "
            "(transform_type, source_data_resource_id, "
            "target_data_resource_id, source_plugin, params) VALUES "
            "('sql', 'garmin.act', 'metrics.daily', 'garmin', "
            "'{\"sql\": \"SELECT 1 AS id, ''garmin'' AS source\"}')"
        )
        row = test_con.execute("SELECT id FROM transforms.instances LIMIT 1").fetchone()
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

        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=FakePlugin):
            result = _gql(client, '{ configValue(kind: "source", name: "garmin", key: "start_date") }')
        assert "errors" not in result
        assert result["data"]["configValue"] == "2024-01-01"

    def test_config_value_query_not_found(self, client: TestClient) -> None:
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=None):
            result = _gql(client, '{ configValue(kind: "source", name: "garmin", key: "missing") }')
        assert "errors" not in result
        assert result["data"]["configValue"] is None


class TestGraphQLMutationsExtra:
    """Coverage for mutations that aren't covered above."""

    def test_authenticate(self, client: TestClient) -> None:
        fake_source = MagicMock()
        fake_source.handle_auth.return_value = {"ok": True, "needs_mfa": False, "auth_url": None, "message": "logged in"}
        fake_cls = MagicMock(return_value=fake_source)
        with patch("shenas_sources.core.source.Source.load_by_name", return_value=fake_cls):
            result = _gql(
                client,
                'mutation { authenticate(source: "garmin", credentials: {username: "u", password: "p"}) { ok message } }',
            )
        assert "errors" not in result
        assert result["data"]["authenticate"]["ok"] is True
        assert result["data"]["authenticate"]["message"] == "logged in"
        fake_source.handle_auth.assert_called_once()

    def test_set_config_success(self, client: TestClient) -> None:
        fake_plugin = MagicMock()
        fake_cls = MagicMock(return_value=fake_plugin)
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=fake_cls):
            result = _gql(
                client,
                'mutation { setConfig(kind: "source", name: "garmin", key: "k", value: "v") { ok } }',
            )
        assert "errors" not in result
        assert result["data"]["setConfig"]["ok"] is True
        fake_plugin.set_config_value.assert_called_once_with("k", "v")

    def test_set_config_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=None):
            result = _gql(
                client,
                'mutation { setConfig(kind: "source", name: "missing", key: "k", value: "v") { ok message } }',
            )
        assert result["data"]["setConfig"]["ok"] is False
        assert "missing" in result["data"]["setConfig"]["message"]

    def test_delete_config_success(self, client: TestClient) -> None:
        fake_plugin = MagicMock()
        fake_cls = MagicMock(return_value=fake_plugin)
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=fake_cls):
            result = _gql(client, 'mutation { deleteConfig(kind: "source", name: "garmin") { ok } }')
        assert result["data"]["deleteConfig"]["ok"] is True
        fake_plugin.delete_config.assert_called_once()

    def test_delete_config_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=None):
            result = _gql(client, 'mutation { deleteConfig(kind: "source", name: "missing") { ok message } }')
        assert result["data"]["deleteConfig"]["ok"] is False

    def test_delete_config_key_success(self, client: TestClient) -> None:
        fake_plugin = MagicMock()
        fake_cls = MagicMock(return_value=fake_plugin)
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=fake_cls):
            result = _gql(
                client,
                'mutation { deleteConfigKey(kind: "source", name: "garmin", key: "k") { ok } }',
            )
        assert result["data"]["deleteConfigKey"]["ok"] is True
        fake_plugin.set_config_value.assert_called_once_with("k", None)

    def test_delete_config_key_plugin_not_found(self, client: TestClient) -> None:
        with patch("app.plugin.Plugin.load_by_name_and_kind", return_value=None):
            result = _gql(
                client,
                'mutation { deleteConfigKey(kind: "source", name: "missing", key: "k") { ok message } }',
            )
        assert result["data"]["deleteConfigKey"]["ok"] is False

    def test_generate_db_key(self, client: TestClient) -> None:
        with patch("app.database.generate_db_key", return_value="newkey"), patch("app.database.set_db_key") as mock_set:
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
        with patch("app.plugin.Plugin.install", return_value=(True, "installed")):
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
        with patch("app.plugin.Plugin.uninstall", return_value=(True, "removed")):
            result = _gql(
                client,
                'mutation { removePlugin(kind: "source", name: "garmin") { ok message } }',
            )
        assert result["data"]["removePlugin"]["ok"] is True
        assert result["data"]["removePlugin"]["message"] == "removed"

    def test_enable_plugin_creates_if_missing(self, client: TestClient) -> None:
        """Enabling a plugin that has no row yet creates one via get_or_create."""
        result = _gql(
            client,
            'mutation { enablePlugin(kind: "source", name: "missing") { ok } }',
        )
        assert result["data"]["enablePlugin"]["ok"] is True

    def test_disable_plugin_not_found(self, client: TestClient) -> None:
        result = _gql(
            client,
            'mutation { disablePlugin(kind: "source", name: "missing") { ok message } }',
        )
        assert result["data"]["disablePlugin"]["ok"] is False

    def test_seed_transforms(self, client: TestClient) -> None:
        fake_ep = MagicMock()
        fake_ep.name = "garmin"
        fake_plugin_cls = MagicMock()
        fake_plugin_instance = MagicMock()
        fake_plugin_instance.enabled = True
        fake_plugin_cls.return_value = fake_plugin_instance
        with (
            patch("app.graphql.mutations._source_entry_point_names", return_value=["garmin"]),
            patch("shenas_transformers.core.Transformer.load_all", return_value=[fake_plugin_cls]),
        ):
            result = _gql(client, "mutation { seedTransforms { seeded count } }")
        assert "errors" not in result
        assert result["data"]["seedTransforms"]["count"] == 1
        assert result["data"]["seedTransforms"]["seeded"] == ["garmin"]
        fake_plugin_instance.seed_defaults_for_source.assert_called_once_with("garmin")

    def test_seed_transforms_no_sources(self, client: TestClient) -> None:
        with (
            patch("app.graphql.mutations._source_entry_point_names", return_value=[]),
            patch("shenas_transformers.core.Transformer.load_all", return_value=[]),
        ):
            result = _gql(client, "mutation { seedTransforms { seeded count } }")
        assert result["data"]["seedTransforms"]["count"] == 0

    def test_run_source_transforms(self, client: TestClient) -> None:
        with patch("shenas_transformers.core.transform.Transform.run_for_source", return_value=3):
            result = _gql(client, 'mutation { runSourceTransforms(source: "garmin") { name count } }')
        assert "errors" not in result
        assert result["data"]["runSourceTransforms"]["name"] == "garmin"
        assert result["data"]["runSourceTransforms"]["count"] == 3

    def test_run_schema_transforms(self, client: TestClient) -> None:
        with patch("shenas_transformers.core.transform.Transform.run_for_target", return_value=2):
            result = _gql(client, 'mutation { runSchemaTransforms(schema: "metrics") { name count } }')
        assert "errors" not in result
        assert result["data"]["runSchemaTransforms"]["name"] == "metrics"
        assert result["data"]["runSchemaTransforms"]["count"] == 2
