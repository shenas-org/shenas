from contextlib import contextmanager
from typing import Annotated, ClassVar
from unittest.mock import patch

import duckdb
import pytest

from shenas_plugins.core.table import Field, Table


class SampleConfig(Table):
    table_display_name: ClassVar[str] = "Sample Config"
    table_name: ClassVar[str] = "test_pkg"
    table_pk: ClassVar[tuple[str, ...]] = ("id",)
    table_schema: ClassVar[str | None] = "config"

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
    SampleConfig._ensured.discard(("config", "test_pkg"))
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
        SampleConfig.write_row(api_key="secret123")
        row = SampleConfig.read_row()
        assert row is not None
        assert row["api_key"] == "secret123"
        assert row["start_date"] == "30 days ago"  # default

    def test_set_updates_row(self) -> None:
        SampleConfig.write_row(api_key="old")
        SampleConfig.write_row(api_key="new")
        assert SampleConfig.read_value("api_key") == "new"

    def test_partial_update_preserves_others(self) -> None:
        SampleConfig.write_row(api_key="key1", start_date="7 days ago")
        SampleConfig.write_row(start_date="14 days ago")
        row = SampleConfig.read_row()
        assert row is not None
        assert row["api_key"] == "key1"
        assert row["start_date"] == "14 days ago"

    def test_get_empty(self) -> None:
        assert SampleConfig.read_row() is None

    def test_get_value_empty(self) -> None:
        assert SampleConfig.read_value("api_key") is None


class TestDelete:
    def test_delete(self) -> None:
        SampleConfig.write_row(api_key="key")
        SampleConfig.clear_rows()
        assert SampleConfig.read_row() is None


class TestMetadata:
    def test_returns_columns(self) -> None:
        meta = SampleConfig.table_metadata()
        assert meta["table"] == "test_pkg"
        names = [c["name"] for c in meta["columns"]]
        assert "api_key" in names
        assert "start_date" in names

    def test_secret_category(self) -> None:
        meta = SampleConfig.table_metadata()
        api_key = next(c for c in meta["columns"] if c["name"] == "api_key")
        assert api_key["category"] == "secret"
        assert api_key["ui_widget"] == "password"

    def test_default_value(self) -> None:
        meta = SampleConfig.table_metadata()
        start = next(c for c in meta["columns"] if c["name"] == "start_date")
        assert start.get("default") == "30 days ago"
        assert start["ui_widget"] == "text"
