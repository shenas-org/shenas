"""Tests for app.hypotheses.Hypothesis CRUD + (de)serialization."""

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
    def _fake_cursor(**_kwargs) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        cur = db_con.cursor()
        try:
            cur.execute("USE db")
            yield cur
        finally:
            cur.close()

    with patch("app.db.cursor", _fake_cursor):
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
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("does caffeine affect mood?", _recipe(), plan="join then correlate", model="anthropic@x@0")
    assert h.question == "does caffeine affect mood?"
    assert h.plan == "join then correlate"
    assert h.model == "anthropic@x@0"
    assert "metrics.daily_intake" in h.inputs  # ty: ignore[unsupported-operator]
    assert "metrics.daily_outcomes" in h.inputs  # ty: ignore[unsupported-operator]
    assert h.id > 0  # populated from sequence

    found = Hypothesis.find(h.id)
    assert found is not None
    assert found.question == h.question


def test_recipe_round_trip():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    recovered = Hypothesis.find(h.id).recipe()  # ty: ignore[unresolved-attribute]
    assert recovered.final == "r"
    assert isinstance(recovered.nodes["a"], SourceRef)
    assert recovered.nodes["a"].table == "metrics.daily_intake"
    assert isinstance(recovered.nodes["j"], OpCall)
    assert recovered.nodes["j"].op_name == "join_as_of"
    assert recovered.nodes["j"].inputs == ("a", "b")
    assert recovered.nodes["r"].params == {"x": "caffeine_mg", "y": "mood"}  # ty: ignore[unresolved-attribute]


def test_all_returns_instances():
    from app.hypotheses import Hypothesis

    Hypothesis.create("q1", _recipe())
    Hypothesis.create("q2", _recipe())
    rows = Hypothesis.all(order_by="created_at DESC")
    assert len(rows) == 2
    assert {r.question for r in rows} == {"q1", "q2"}
    assert all(isinstance(r, Hypothesis) for r in rows)


def test_attach_result_scalar():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    h.attach_result(ScalarResult(value=-0.95, column="corr", elapsed_ms=12.0, sql="SELECT 1"))
    res = Hypothesis.find(h.id).result()  # ty: ignore[unresolved-attribute]
    assert isinstance(res, ScalarResult)
    assert res.value == -0.95
    assert res.column == "corr"


def test_attach_result_table():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    h.attach_result(
        TableResult(rows=[{"a": 1}], columns=["a"], row_count=1, truncated=False, elapsed_ms=1.0, sql="SELECT a"),
    )
    res = Hypothesis.find(h.id).result()  # ty: ignore[unresolved-attribute]
    assert isinstance(res, TableResult)
    assert res.rows == [{"a": 1}]
    assert res.columns == ["a"]


def test_attach_result_error():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    h.attach_result(ErrorResult(message="boom", kind="execution", elapsed_ms=2.0, sql=""))
    res = Hypothesis.find(h.id).result()  # ty: ignore[unresolved-attribute]
    assert isinstance(res, ErrorResult)
    assert res.message == "boom"
    assert res.kind == "execution"


def test_result_none_when_unset():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    assert Hypothesis.find(h.id).result() is None  # ty: ignore[unresolved-attribute]


def test_attach_interpretation():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    h.attach_interpretation("strong negative correlation")
    assert Hypothesis.find(h.id).interpretation == "strong negative correlation"  # ty: ignore[unresolved-attribute]


def test_mark_promoted():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    h.mark_promoted("metrics.caffeine_mood_corr")
    assert Hypothesis.find(h.id).promoted_to == "metrics.caffeine_mood_corr"  # ty: ignore[unresolved-attribute]


def test_delete_idempotent():
    from app.hypotheses import Hypothesis

    h = Hypothesis.create("q", _recipe())
    hid = h.id
    h.delete()
    assert Hypothesis.find(hid) is None
    h.delete()  # no error


def test_save_missing_raises():
    from app.hypotheses import Hypothesis

    ghost = Hypothesis(id=999999, question="never inserted")
    with pytest.raises(ValueError, match="found no row"):
        ghost.attach_interpretation("x")
