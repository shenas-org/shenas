"""Tests for the config CRUD API endpoints."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, ClassVar
from unittest.mock import patch

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.server import app
from shenas_schemas.core.field import Field


@dataclass
class _FakeConfig:
    __table__: ClassVar[str] = "pipe_testpipe"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Primary key")] = 1
    api_key: Annotated[str, Field(db_type="VARCHAR", description="API key", category="secret")] | None = None
    username: Annotated[str, Field(db_type="VARCHAR", description="Username")] | None = None


FAKE_CLASSES = {"pipe_testpipe": _FakeConfig}


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.api.config import _config

    _config._ensured.discard("pipe_testpipe")
    con = duckdb.connect(":memory:")

    @contextmanager
    def _fake_cursor():
        cur = con.cursor()
        try:
            yield cur
        finally:
            cur.close()

    with (
        patch("shenas_pipes.core.store.cursor", _fake_cursor),
        patch("app.api.config._discover_config_classes", return_value=FAKE_CLASSES),
    ):
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

    def test_list_filter_by_kind_only(self, client: TestClient) -> None:
        resp = client.get("/api/config?kind=pipe")
        assert resp.status_code == 200

    def test_list_filter_unknown_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/config?kind=pipe&name=nonexistent")
        assert resp.status_code == 404

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

    def test_get_unknown_config(self, client: TestClient) -> None:
        resp = client.get("/api/config/pipe/nonexistent/key")
        assert resp.status_code == 404


class TestSetConfig:
    def test_set_value(self, client: TestClient) -> None:
        resp = client.put("/api/config/pipe/testpipe", json={"key": "username", "value": "bob"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "message": ""}

    def test_set_unknown_config(self, client: TestClient) -> None:
        resp = client.put("/api/config/pipe/nonexistent", json={"key": "foo", "value": "bar"})
        assert resp.status_code == 404


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

    def test_delete_unknown_config(self, client: TestClient) -> None:
        resp = client.delete("/api/config/pipe/nonexistent")
        assert resp.status_code == 404
