"""Tests for the config CRUD API endpoints."""

from collections.abc import Iterator
from unittest.mock import patch

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.server import app

CONFIG_MOD = "shenas_pipes.core.config"


# Fake config class for testing
class _FakeConfig:
    __table__ = "pipe_testpipe"


FAKE_CLASSES = {"pipe_testpipe": _FakeConfig}

FAKE_METADATA = {
    "columns": [
        {"name": "id", "description": "Primary key"},
        {"name": "api_key", "description": "API key", "category": "secret"},
        {"name": "username", "description": "Username"},
    ]
}


@pytest.fixture()
def test_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


@pytest.fixture()
def client(test_con: duckdb.DuckDBPyConnection) -> Iterator[TestClient]:
    with (
        patch("app.api.config.connect", return_value=test_con),
        patch("app.api.config._discover_config_classes", return_value=FAKE_CLASSES),
    ):
        yield TestClient(app)


class TestListConfigs:
    def test_list_all(self, client: TestClient) -> None:
        fake_row = {"id": 1, "api_key": "secret123", "username": "alice"}
        with (
            patch(f"{CONFIG_MOD}.get_config", return_value=fake_row),
            patch(f"{CONFIG_MOD}.config_metadata", return_value=FAKE_METADATA),
        ):
            resp = client.get("/api/config")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["kind"] == "pipe"
        assert data[0]["name"] == "testpipe"

    def test_list_masks_secrets(self, client: TestClient) -> None:
        fake_row = {"id": 1, "api_key": "secret123", "username": "alice"}
        with (
            patch(f"{CONFIG_MOD}.get_config", return_value=fake_row),
            patch(f"{CONFIG_MOD}.config_metadata", return_value=FAKE_METADATA),
        ):
            resp = client.get("/api/config")

        entries = {e["key"]: e["value"] for e in resp.json()[0]["entries"]}
        assert entries["api_key"] == "********"
        assert entries["username"] == "alice"

    def test_list_null_values(self, client: TestClient) -> None:
        fake_row = {"id": 1, "api_key": None, "username": None}
        with (
            patch(f"{CONFIG_MOD}.get_config", return_value=fake_row),
            patch(f"{CONFIG_MOD}.config_metadata", return_value=FAKE_METADATA),
        ):
            resp = client.get("/api/config")

        entries = {e["key"]: e["value"] for e in resp.json()[0]["entries"]}
        assert entries["api_key"] is None
        assert entries["username"] is None

    def test_list_no_config_row(self, client: TestClient) -> None:
        with (
            patch(f"{CONFIG_MOD}.get_config", return_value=None),
            patch(f"{CONFIG_MOD}.config_metadata", return_value=FAKE_METADATA),
        ):
            resp = client.get("/api/config")

        entries = {e["key"]: e["value"] for e in resp.json()[0]["entries"]}
        assert entries["api_key"] is None

    def test_list_filter_by_kind_and_name(self, client: TestClient) -> None:
        with (
            patch(f"{CONFIG_MOD}.get_config", return_value={"id": 1, "api_key": "x", "username": "y"}),
            patch(f"{CONFIG_MOD}.config_metadata", return_value=FAKE_METADATA),
        ):
            resp = client.get("/api/config?kind=pipe&name=testpipe")

        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_filter_by_kind_only(self, client: TestClient) -> None:
        with (
            patch(f"{CONFIG_MOD}.get_config", return_value={"id": 1, "api_key": "x", "username": "y"}),
            patch(f"{CONFIG_MOD}.config_metadata", return_value=FAKE_METADATA),
        ):
            resp = client.get("/api/config?kind=pipe")

        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["kind"] == "pipe"

    def test_list_filter_unknown_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/config?kind=pipe&name=nonexistent")
        assert resp.status_code == 404

    def test_list_filter_kind_no_match(self, client: TestClient) -> None:
        resp = client.get("/api/config?kind=schema")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_excludes_id_column(self, client: TestClient) -> None:
        fake_row = {"id": 1, "api_key": "x", "username": "y"}
        with (
            patch(f"{CONFIG_MOD}.get_config", return_value=fake_row),
            patch(f"{CONFIG_MOD}.config_metadata", return_value=FAKE_METADATA),
        ):
            resp = client.get("/api/config")

        keys = [e["key"] for e in resp.json()[0]["entries"]]
        assert "id" not in keys


class TestGetConfigValue:
    def test_get_existing_value(self, client: TestClient) -> None:
        with patch(f"{CONFIG_MOD}.get_config_value", return_value="alice"):
            resp = client.get("/api/config/pipe/testpipe/username")

        assert resp.status_code == 200
        assert resp.json() == {"key": "username", "value": "alice"}

    def test_get_not_set(self, client: TestClient) -> None:
        with patch(f"{CONFIG_MOD}.get_config_value", return_value=None):
            resp = client.get("/api/config/pipe/testpipe/username")

        assert resp.status_code == 404

    def test_get_unknown_config(self, client: TestClient) -> None:
        resp = client.get("/api/config/pipe/nonexistent/key")
        assert resp.status_code == 404


class TestSetConfig:
    def test_set_value(self, client: TestClient) -> None:
        with patch(f"{CONFIG_MOD}.set_config") as mock_set:
            resp = client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "bob"})

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_set.assert_called_once()

    def test_set_unknown_config(self, client: TestClient) -> None:
        resp = client.put("/api/config/pipe/nonexistent", json={"key": "foo", "value": "bar"})
        assert resp.status_code == 404


class TestDeleteConfig:
    def test_delete_all(self, client: TestClient) -> None:
        with patch(f"{CONFIG_MOD}.delete_config"):
            resp = client.delete("/api/config/pipe/testpipe")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_delete_single_key(self, client: TestClient) -> None:
        with patch(f"{CONFIG_MOD}.set_config"):
            resp = client.delete("/api/config/pipe/testpipe/username")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_delete_unknown_config(self, client: TestClient) -> None:
        resp = client.delete("/api/config/pipe/nonexistent")
        assert resp.status_code == 404
