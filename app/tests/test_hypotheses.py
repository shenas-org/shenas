"""Tests for app.hypotheses.HypothesisRecord CRUD + (de)serialization."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest.mock import patch

import duckdb
import pytest

from shenas_plugins.core.analytics import (
    ErrorResult,
    OpCall,
    Recipe,
    ScalarResult,
    SourceRef,
    TableResult,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator


@pytest.fixture
def db_con() -> Iterator[duckdb.DuckDBPyConnection]:
    con = duckdb.connect(":memory:")
    con.execute("ATTACH ':memory:' AS db")
    con.execute("USE db")
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")
    from app.db import _ensure_system_tables

    _ensure_system_tables(con)
    yield con
    con.close()


@pytest.fixture(autouse=True)
def patch_db(db_con: duckdb.DuckDBPyConnection) -> Iterator[None]:
    @contextlib.contextmanager
    def _fake_cursor() -> Generator[duckdb.DuckDBPyConnection, None, None]:
        cur = db_con.cursor()
        try:
            cur.execute("USE db")
            yield cur
        finally:
            cur.close()

    with patch("app.db.cursor", _fake_cursor), patch("app.hypotheses.cursor", _fake_cursor):
        yield


def _recipe() -> Recipe:
    return Recipe(
        nodes={
            "a": SourceRef(table="metrics.daily_intake"),
            "b": SourceRef(table="metrics.daily_outcomes"),
            "j": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("a", "b")),
            "r": OpCall(op_name="correlate", params={"x": "caffeine_mg", "y": "mood"}, inputs=("j",)),
        },
        final="r",
    )


def test_create_and_find():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("does caffeine affect mood?", _recipe(), plan="join then correlate", model="anthropic@x@0")
    assert h["question"] == "does caffeine affect mood?"
    assert h["plan"] == "join then correlate"
    assert h["model"] == "anthropic@x@0"
    assert "metrics.daily_intake" in h["inputs"]
    assert "metrics.daily_outcomes" in h["inputs"]

    found = HypothesisRecord.find(h["id"])
    assert found is not None
    assert found["question"] == h["question"]


def test_recipe_round_trip():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    recovered = HypothesisRecord.find(h["id"]).recipe()
    assert recovered.final == "r"
    assert isinstance(recovered.nodes["a"], SourceRef)
    assert recovered.nodes["a"].table == "metrics.daily_intake"
    assert isinstance(recovered.nodes["j"], OpCall)
    assert recovered.nodes["j"].op_name == "join_as_of"
    assert recovered.nodes["j"].inputs == ("a", "b")
    assert recovered.nodes["r"].params == {"x": "caffeine_mg", "y": "mood"}


def test_all_orders_recent_first():
    from app.hypotheses import HypothesisRecord

    HypothesisRecord.create("q1", _recipe())
    HypothesisRecord.create("q2", _recipe())
    rows = HypothesisRecord.all()
    assert len(rows) == 2
    assert {r["question"] for r in rows} == {"q1", "q2"}


def test_attach_result_scalar():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    HypothesisRecord.attach_result(h["id"], ScalarResult(value=-0.95, column="corr", elapsed_ms=12.0, sql="SELECT 1"))
    res = HypothesisRecord.find(h["id"]).result()
    assert isinstance(res, ScalarResult)
    assert res.value == -0.95
    assert res.column == "corr"


def test_attach_result_table():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    HypothesisRecord.attach_result(
        h["id"],
        TableResult(rows=[{"a": 1}], columns=["a"], row_count=1, truncated=False, elapsed_ms=1.0, sql="SELECT a"),
    )
    res = HypothesisRecord.find(h["id"]).result()
    assert isinstance(res, TableResult)
    assert res.rows == [{"a": 1}]
    assert res.columns == ["a"]


def test_attach_result_error():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    HypothesisRecord.attach_result(h["id"], ErrorResult(message="boom", kind="execution", elapsed_ms=2.0, sql=""))
    res = HypothesisRecord.find(h["id"]).result()
    assert isinstance(res, ErrorResult)
    assert res.message == "boom"
    assert res.kind == "execution"


def test_result_none_when_unset():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    assert HypothesisRecord.find(h["id"]).result() is None


def test_attach_interpretation():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    HypothesisRecord.attach_interpretation(h["id"], "strong negative correlation")
    assert HypothesisRecord.find(h["id"])["interpretation"] == "strong negative correlation"


def test_mark_promoted():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    HypothesisRecord.mark_promoted(h["id"], "metrics.caffeine_mood_corr")
    assert HypothesisRecord.find(h["id"])["promoted_to"] == "metrics.caffeine_mood_corr"


def test_delete_idempotent():
    from app.hypotheses import HypothesisRecord

    h = HypothesisRecord.create("q", _recipe())
    HypothesisRecord.delete(h["id"])
    assert HypothesisRecord.find(h["id"]) is None
    HypothesisRecord.delete(h["id"])  # no error


def test_attach_to_missing_raises():
    from app.hypotheses import HypothesisRecord

    with pytest.raises(ValueError, match="not found"):
        HypothesisRecord.attach_interpretation(999999, "x")
