from dataclasses import dataclass
from typing import Annotated, ClassVar

import duckdb
import pytest

from shenas_pipes.core.config import config_metadata, delete_config, get_config, get_config_value, set_config
from shenas_schemas.core.field import Field


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


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


class TestSetAndGet:
    def test_set_creates_row(self, con: duckdb.DuckDBPyConnection) -> None:
        set_config(con, SampleConfig, api_key="secret123")
        row = get_config(con, SampleConfig)
        assert row is not None
        assert row["api_key"] == "secret123"
        assert row["start_date"] == "30 days ago"  # default

    def test_set_updates_row(self, con: duckdb.DuckDBPyConnection) -> None:
        set_config(con, SampleConfig, api_key="old")
        set_config(con, SampleConfig, api_key="new")
        assert get_config_value(con, SampleConfig, "api_key") == "new"

    def test_partial_update_preserves_others(self, con: duckdb.DuckDBPyConnection) -> None:
        set_config(con, SampleConfig, api_key="key1", start_date="7 days ago")
        set_config(con, SampleConfig, start_date="14 days ago")
        row = get_config(con, SampleConfig)
        assert row is not None
        assert row["api_key"] == "key1"
        assert row["start_date"] == "14 days ago"

    def test_get_empty(self, con: duckdb.DuckDBPyConnection) -> None:
        assert get_config(con, SampleConfig) is None

    def test_get_value_empty(self, con: duckdb.DuckDBPyConnection) -> None:
        assert get_config_value(con, SampleConfig, "api_key") is None


class TestDelete:
    def test_delete(self, con: duckdb.DuckDBPyConnection) -> None:
        set_config(con, SampleConfig, api_key="key")
        delete_config(con, SampleConfig)
        assert get_config(con, SampleConfig) is None


class TestMetadata:
    def test_returns_columns(self) -> None:
        meta = config_metadata(SampleConfig)
        assert meta["table"] == "test_pkg"
        names = [c["name"] for c in meta["columns"]]
        assert "api_key" in names
        assert "start_date" in names

    def test_secret_category(self) -> None:
        meta = config_metadata(SampleConfig)
        api_key = [c for c in meta["columns"] if c["name"] == "api_key"][0]
        assert api_key["category"] == "secret"
        assert api_key["ui_widget"] == "password"

    def test_default_value(self) -> None:
        meta = config_metadata(SampleConfig)
        start = [c for c in meta["columns"] if c["name"] == "start_date"][0]
        assert start.get("default") == "30 days ago"
        assert start["ui_widget"] == "text"
