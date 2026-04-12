"""Tests for app.recipe_cache."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest.mock import patch

import duckdb
import pytest

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator


@pytest.fixture
def db_con() -> Iterator[duckdb.DuckDBPyConnection]:
    con = duckdb.connect(":memory:")
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    from app.database import _ensure_system_tables

    _ensure_system_tables(con)
    yield con
    con.close()


@pytest.fixture(autouse=True)
def patch_db(db_con: duckdb.DuckDBPyConnection) -> Iterator[None]:
    @contextlib.contextmanager
    def _fake_cursor(**_kwargs) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        cur = db_con.cursor()
        try:
            cur.execute("USE db")
            yield cur
        finally:
            cur.close()

    with patch("app.database.cursor", _fake_cursor):
        yield


def test_cache_key_is_deterministic_and_recipe_sensitive():
    from app.recipe_cache import RecipeCache

    a = RecipeCache.key_for('{"nodes":{},"final":""}', [])
    b = RecipeCache.key_for('{"nodes":{},"final":""}', [])
    c = RecipeCache.key_for('{"nodes":{"x":{}},"final":"x"}', [])
    assert a == b
    assert a != c


def test_cache_key_includes_input_freshness():
    """Adding/removing an input table should change the key."""
    from app.recipe_cache import RecipeCache

    k1 = RecipeCache.key_for('{"nodes":{},"final":""}', [])
    k2 = RecipeCache.key_for('{"nodes":{},"final":""}', ["metrics.daily_intake"])
    assert k1 != k2


def test_put_and_find_round_trip():
    from app.recipe_cache import RecipeCache

    payload = {"type": "scalar", "value": 0.42, "column": "corr"}
    RecipeCache.put("abc123", payload)
    row = RecipeCache.find("abc123")
    assert row is not None
    assert row.payload == payload


def test_find_miss_returns_none():
    from app.recipe_cache import RecipeCache

    assert RecipeCache.find("never-stored") is None


def test_clear_rows_drops_everything():
    from app.recipe_cache import RecipeCache

    RecipeCache.put("k1", {"type": "scalar", "value": 1})
    RecipeCache.put("k2", {"type": "scalar", "value": 2})
    RecipeCache.clear_rows()
    assert RecipeCache.find("k1") is None
    assert RecipeCache.find("k2") is None


def test_payload_property_handles_empty_and_invalid_json():
    from app.recipe_cache import RecipeCache

    empty = RecipeCache(cache_key="x", result_json="")
    assert empty.payload is None
    bad = RecipeCache(cache_key="y", result_json="{not json")
    assert bad.payload is None
