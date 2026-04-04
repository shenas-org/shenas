"""Tests for the config CRUD API endpoints."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.server import app
from shenas_pipes.core.pipe import Pipe
from shenas_plugins.core.base_config import PipeConfig
from shenas_schemas.core.field import Field


@dataclass
class _TestConfig(PipeConfig):
    __table__: ClassVar[str] = "pipe_testpipe"
    api_key: Annotated[str, Field(db_type="VARCHAR", description="API key", category="secret")] | None = None
    username: Annotated[str, Field(db_type="VARCHAR", description="Username")] | None = None


class _TestPipe(Pipe):
    name = "testpipe"
    display_name = "Test Pipe"
    Config = _TestConfig

    def resources(self, client: Any) -> list[Any]:
        return []


@pytest.fixture
def client() -> Iterator[TestClient]:

    con = duckdb.connect(":memory:")

    @contextmanager
    def _fake_cursor():
        cur = con.cursor()
        try:
            yield cur
        finally:
            cur.close()

    pipe = _TestPipe()

    with (
        patch("shenas_plugins.core.store.cursor", _fake_cursor),
        patch("app.api.config._load_plugin", return_value=_TestPipe),
        patch("app.api.config._load_plugins", side_effect=lambda k, **_kw: [_TestPipe] if k == "pipe" else []),
        patch("app.db.get_plugin_state", return_value=None),
    ):
        # Clear the ensured cache so tables get created in the in-memory DB
        for store in (pipe._config_store, pipe._auth_store):
            store._ensured.discard("pipe_testpipe")
        yield TestClient(app)


class TestListConfigs:
    def test_list_all(self, client: TestClient) -> None:
        client.put("/api/config/pipe/testpipe", json={"key": "api_key", "value": "secret123"})
        client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "alice"})
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["kind"] == "pipe"
        assert data[0]["name"] == "testpipe"

    def test_list_masks_secrets(self, client: TestClient) -> None:
        client.put("/api/config/pipe/testpipe", json={"key": "api_key", "value": "secret123"})
        client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "alice"})
        resp = client.get("/api/config")
        entries = {e["key"]: e["value"] for e in resp.json()[0]["entries"]}
        assert entries["api_key"] == "********"
        assert entries["username"] == "alice"

    def test_list_null_values(self, client: TestClient) -> None:
        resp = client.get("/api/config")
        entries = {e["key"]: e["value"] for e in resp.json()[0]["entries"]}
        assert entries["api_key"] is None
        assert entries["username"] is None

    def test_list_filter_by_kind_and_name(self, client: TestClient) -> None:
        resp = client.get("/api/config?kind=pipe&name=testpipe")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_filter_kind_no_match(self, client: TestClient) -> None:
        resp = client.get("/api/config?kind=schema")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_excludes_id_column(self, client: TestClient) -> None:
        resp = client.get("/api/config")
        keys = [e["key"] for e in resp.json()[0]["entries"]]
        assert "id" not in keys


class TestGetConfigValue:
    def test_get_existing_value(self, client: TestClient) -> None:
        client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "alice"})
        resp = client.get("/api/config/pipe/testpipe/username")
        assert resp.status_code == 200
        assert resp.json() == {"key": "username", "value": "alice"}

    def test_get_not_set(self, client: TestClient) -> None:
        resp = client.get("/api/config/pipe/testpipe/username")
        assert resp.status_code == 404


class TestSetConfig:
    def test_set_value(self, client: TestClient) -> None:
        resp = client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "bob"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "message": ""}


class TestDeleteConfig:
    def test_delete_all(self, client: TestClient) -> None:
        client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "alice"})
        resp = client.delete("/api/config/pipe/testpipe")
        assert resp.status_code == 200
        assert client.get("/api/config/pipe/testpipe/username").status_code == 404

    def test_delete_single_key(self, client: TestClient) -> None:
        client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "alice"})
        resp = client.delete("/api/config/pipe/testpipe/username")
        assert resp.status_code == 200
