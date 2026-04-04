from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, ClassVar
from unittest.mock import patch

import duckdb
import pytest

from shenas_plugins.core.store import DataclassStore
from shenas_schemas.core.field import Field

_config = DataclassStore("config")


def get_config(cls):
    return _config.get(cls)


def get_config_value(cls, key):
    return _config.get_value(cls, key)


def set_config(cls, **kwargs):
    _config.set(cls, **kwargs)


def delete_config(cls):
    _config.delete(cls)


def config_metadata(cls):
    return _config.metadata(cls)


@dataclass
class SampleConfig:
    __table__: ClassVar[str] = "test_pkg"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Row ID")] = 1
    api_key: (
        Annotated[str, Field(db_type="VARCHAR", description="API key", category="secret", ui_widget="password")] | None
    ) = None
    start_date: Annotated[str, Field(db_type="VARCHAR", description="Start date", default="30 days ago", ui_widget="text")] = (
        "30 days ago"
    )
    count: Annotated[int, Field(db_type="INTEGER", description="A count", value_range=(0, 100))] | None = None


@pytest.fixture(autouse=True)
def _mock_cursor():
    _config._ensured.discard("test_pkg")
    con = duckdb.connect(":memory:")
    con.execute("CREATE SCHEMA IF NOT EXISTS config")

    @contextmanager
    def _fake_cursor():
        cur = con.cursor()
        try:
            yield cur
        finally:
            cur.close()

    with patch("app.db.cursor", _fake_cursor):
        yield


class TestSetAndGet:
    def test_set_creates_row(self) -> None:
        set_config(SampleConfig, api_key="secret123")
        row = get_config(SampleConfig)
        assert row is not None
        assert row["api_key"] == "secret123"
        assert row["start_date"] == "30 days ago"  # default

    def test_set_updates_row(self) -> None:
        set_config(SampleConfig, api_key="old")
        set_config(SampleConfig, api_key="new")
        assert get_config_value(SampleConfig, "api_key") == "new"

    def test_partial_update_preserves_others(self) -> None:
        set_config(SampleConfig, api_key="key1", start_date="7 days ago")
        set_config(SampleConfig, start_date="14 days ago")
        row = get_config(SampleConfig)
        assert row is not None
        assert row["api_key"] == "key1"
        assert row["start_date"] == "14 days ago"

    def test_get_empty(self) -> None:
        assert get_config(SampleConfig) is None

    def test_get_value_empty(self) -> None:
        assert get_config_value(SampleConfig, "api_key") is None


class TestDelete:
    def test_delete(self) -> None:
        set_config(SampleConfig, api_key="key")
        delete_config(SampleConfig)
        assert get_config(SampleConfig) is None


class TestMetadata:
    def test_returns_columns(self) -> None:
        meta = config_metadata(SampleConfig)
        assert meta["table"] == "test_pkg"
        names = [c["name"] for c in meta["columns"]]
        assert "api_key" in names
        assert "start_date" in names

    def test_secret_category(self) -> None:
        meta = config_metadata(SampleConfig)
        api_key = next(c for c in meta["columns"] if c["name"] == "api_key")
        assert api_key["category"] == "secret"
        assert api_key["ui_widget"] == "password"

    def test_default_value(self) -> None:
        meta = config_metadata(SampleConfig)
        start = next(c for c in meta["columns"] if c["name"] == "start_date")
        assert start.get("default") == "30 days ago"
        assert start["ui_widget"] == "text"
