"""Tests for app.recipe_cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def db_con() -> Iterator[duckdb.DuckDBPyConnection]:
    import app.database
    import app.db

    con = duckdb.connect(":memory:")
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    from app.tests.conftest import _StubDB

    stub = _StubDB(con)
    saved = dict(app.db._resolvers)
    app.db._resolvers["shenas"] = lambda: stub  # ty: ignore[invalid-assignment]
    app.db._resolvers[None] = lambda: stub  # ty: ignore[invalid-assignment]
    app.database._ensure_system_tables(con)
    yield con
    app.db._resolvers.clear()
    app.db._resolvers.update(saved)
    con.close()


@pytest.fixture(autouse=True)
def patch_db(db_con: duckdb.DuckDBPyConnection) -> Iterator[None]:
    """Back-compat alias -- db_con already wires the resolvers."""
    return  # ty: ignore[invalid-return-type]


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
