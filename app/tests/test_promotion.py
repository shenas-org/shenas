"""Tests for app.promotion.

Promotion writes to ``analysis.promoted_metrics`` and the
``PromotedSchema`` dataset synthesizes ``MetricTable`` subclasses
from the rows at catalog-walk time. No filesystem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import pytest
from shenas_analyses.core.analytics import OpCall, Recipe, ScalarResult, SourceRef, TableResult

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


def _hypothesis():
    from app.hypotheses import Hypothesis

    recipe = Recipe(
        nodes={
            "a": SourceRef(table="metrics.daily_intake"),
            "b": SourceRef(table="metrics.daily_outcomes"),
            "j": OpCall(op_name="join_as_of", params={"on": "date"}, inputs=("a", "b")),
            "r": OpCall(op_name="correlate", params={"x": "caffeine_mg", "y": "mood"}, inputs=("j",)),
        },
        final="r",
    )
    return Hypothesis.create("does coffee affect mood?", recipe, plan="join then correlate")


def test_validates_snake_case_name():
    from app.promotion import promote_hypothesis

    h = _hypothesis()
    with pytest.raises(ValueError, match="snake_case"):
        promote_hypothesis(h, name="MyMetric")


def test_refuses_overwriting_existing_row():
    from app.promotion import promote_hypothesis

    h = _hypothesis()
    promote_hypothesis(h, name="caffeine_mood")
    with pytest.raises(ValueError, match="already exists"):
        promote_hypothesis(h, name="caffeine_mood")


def test_refuses_promoting_empty_recipe():
    from app.hypotheses import Hypothesis
    from app.promotion import promote_hypothesis

    h = Hypothesis.create("q", Recipe(nodes={}, final=""))
    h.recipe_json = ""
    h.save()
    with pytest.raises(ValueError, match="no recipe"):
        promote_hypothesis(h, name="some_metric")


def test_inserts_row_with_provenance():
    from app.promotion import promote_hypothesis
    from shenas_datasets.promoted import PromotedMetric

    h = _hypothesis()
    h.attach_result(
        TableResult(
            rows=[{"date": "2026-01-01", "source": "manual", "corr": -0.5}],
            columns=["date", "source", "corr"],
            row_count=1,
            truncated=False,
        )
    )
    record = promote_hypothesis(h, name="caffeine_mood")
    assert record.qualified == "datasets.caffeine_mood"
    assert record.hypothesis_id == h.id

    row = PromotedMetric.find("caffeine_mood", "datasets")
    assert row is not None
    assert row.hypothesis_id == h.id
    assert row.recipe_json == h.recipe_json
    assert "metrics.daily_intake" in row.inputs


def test_marks_hypothesis_promoted():
    from app.hypotheses import Hypothesis
    from app.promotion import promote_hypothesis

    h = _hypothesis()
    promote_hypothesis(h, name="caffeine_mood")
    refreshed = Hypothesis.find(h.id)
    assert refreshed is not None
    assert refreshed.promoted_to == "datasets.caffeine_mood"


def test_synthesized_class_carries_meta_and_provenance():
    import dataclasses

    from app.promotion import promote_hypothesis
    from shenas_datasets.promoted import PromotedSchema

    h = _hypothesis()
    h.attach_result(
        TableResult(
            rows=[{"date": "2026-01-01", "source": "m", "corr": -0.5}],
            columns=["date", "source", "corr"],
            row_count=1,
            truncated=False,
        )
    )
    promote_hypothesis(h, name="caffeine_mood")

    classes = list(PromotedSchema.all_tables)
    assert len(classes) == 1
    cls = classes[0]
    assert cls._Meta.name == "caffeine_mood"
    assert cls._Meta.schema == "datasets"
    assert cls._Meta.pk == ("date", "source")
    assert cls.promoted_from_hypothesis == h.id
    assert "metrics.daily_intake" in cls.derived_from
    field_names = {f.name for f in dataclasses.fields(cls)}
    assert field_names == {"date", "source", "corr"}


def test_scalar_result_synthesizes_value_field():
    import dataclasses

    from app.promotion import promote_hypothesis
    from shenas_datasets.promoted import PromotedSchema

    h = _hypothesis()
    h.attach_result(ScalarResult(value=-0.42, column="corr"))
    promote_hypothesis(h, name="caffeine_mood_corr")
    classes = list(PromotedSchema.all_tables)
    cls = next(c for c in classes if c._Meta.name == "caffeine_mood_corr")
    field_names = {f.name for f in dataclasses.fields(cls)}
    assert "id" in field_names
    assert "value" in field_names


def test_promoted_schema_empty_when_no_promotions():
    from shenas_datasets.promoted import PromotedSchema

    assert list(PromotedSchema.all_tables) == []
