"""Tests for app.literature.Finding CRUD, category matching, and suggestions."""

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


def _make_finding(**overrides):
    from app.literature import Finding

    defaults = {
        "exposure": "sleep_quality",
        "outcome": "heart_rate_variability",
        "direction": "positive",
        "effect_size": 0.42,
        "effect_size_type": "r",
        "lag_hours": 0.0,
        "lag_max_hours": 8.0,
        "evidence_level": "meta_analysis",
        "sample_size": 2400,
        "population": "healthy_adults",
        "mechanism": "Deep sleep promotes parasympathetic recovery",
        "citation": "Smith et al., 2023, Sleep Medicine Reviews",
        "source_kind": "curated",
        "exposure_categories": "sleep",
        "outcome_categories": "cardiovascular",
    }
    defaults.update(overrides)
    return Finding(**defaults)


def test_insert_and_find():
    f = _make_finding()
    f.insert()
    assert f.id > 0

    found = type(f).find(f.id)
    assert found is not None
    assert found.exposure == "sleep_quality"
    assert found.outcome == "heart_rate_variability"
    assert found.effect_size == 0.42


def test_all_returns_instances():
    from app.literature import Finding

    _make_finding(exposure="a").insert()
    _make_finding(exposure="b").insert()
    rows = Finding.all()
    assert len(rows) == 2
    assert all(isinstance(r, Finding) for r in rows)


def test_for_categories_matches_exposure():
    from app.literature import Finding

    _make_finding(exposure_categories="sleep", outcome_categories="cardiovascular").insert()
    _make_finding(exposure_categories="activity", outcome_categories="wellbeing").insert()

    results = Finding.for_categories("sleep")
    assert len(results) == 1
    assert results[0].exposure_categories == "sleep"


def test_for_categories_matches_outcome():
    from app.literature import Finding

    _make_finding(exposure_categories="activity", outcome_categories="cardiovascular").insert()
    results = Finding.for_categories("cardiovascular")
    assert len(results) == 1


def test_for_categories_multiple():
    from app.literature import Finding

    _make_finding(exposure_categories="sleep", outcome_categories="cardiovascular").insert()
    _make_finding(exposure_categories="activity", outcome_categories="wellbeing").insert()
    _make_finding(exposure_categories="spending", outcome_categories="performance").insert()

    results = Finding.for_categories("sleep", "wellbeing")
    assert len(results) == 2


def test_for_categories_empty():
    from app.literature import Finding

    assert Finding.for_categories() == []


def test_by_source_ref():
    from app.literature import Finding

    _make_finding(source_ref="W12345").insert()
    found = Finding.by_source_ref("W12345")
    assert found is not None
    assert found.source_ref == "W12345"

    assert Finding.by_source_ref("W99999") is None


def test_to_prompt_line():
    f = _make_finding()
    line = f.to_prompt_line()
    assert "sleep_quality -> heart_rate_variability" in line
    assert "positive" in line
    assert "r=0.42" in line
    assert "lag 0.0-8.0h" in line
    assert "meta_analysis" in line
    assert "n=2400" in line
    assert "Mechanism: Deep sleep promotes parasympathetic recovery" in line


def test_to_prompt_line_minimal():
    f = _make_finding(effect_size=None, lag_hours=None, lag_max_hours=None, sample_size=None, mechanism=None)
    line = f.to_prompt_line()
    assert "sleep_quality -> heart_rate_variability" in line
    assert "positive" in line
    assert "lag" not in line


def test_extract_catalog_categories():
    from app.literature import extract_catalog_categories

    catalog = {
        "metrics.daily_hrv": {
            "columns": [
                {"name": "rmssd", "category": "cardiovascular"},
                {"name": "date", "category": "time"},
            ],
        },
        "metrics.daily_sleep": {
            "columns": [
                {"name": "total_hours", "category": "sleep"},
                {"name": "score", "category": "sleep"},
            ],
        },
    }
    cats = extract_catalog_categories(catalog)
    assert cats == {"cardiovascular", "time", "sleep"}


def test_extract_catalog_categories_empty():
    from app.literature import extract_catalog_categories

    assert extract_catalog_categories({}) == set()


def test_suggest_hypotheses():
    from app.literature import suggest_hypotheses

    _make_finding(
        exposure="sleep_quality",
        outcome="heart_rate_variability",
        direction="positive",
        effect_size=0.42,
        evidence_level="meta_analysis",
        exposure_categories="sleep",
        outcome_categories="cardiovascular",
    ).insert()
    _make_finding(
        exposure="exercise",
        outcome="mood",
        direction="positive",
        effect_size=0.35,
        evidence_level="rct",
        exposure_categories="activity",
        outcome_categories="wellbeing",
    ).insert()

    catalog = {
        "metrics.daily_hrv": {"columns": [{"name": "rmssd", "category": "cardiovascular"}]},
        "metrics.daily_sleep": {"columns": [{"name": "score", "category": "sleep"}]},
        "metrics.daily_vitals": {"columns": [{"name": "steps", "category": "activity"}]},
        "metrics.daily_outcomes": {"columns": [{"name": "mood", "category": "wellbeing"}]},
    }
    suggestions = suggest_hypotheses(catalog, limit=10)
    assert len(suggestions) == 2
    # Meta-analysis should rank first
    assert suggestions[0].evidence_level == "meta_analysis"
    assert suggestions[1].evidence_level == "rct"
    assert "sleep" in suggestions[0].question.lower()


def test_suggest_hypotheses_filters_unavailable_data():
    from app.literature import suggest_hypotheses

    _make_finding(
        exposure_categories="spending",
        outcome_categories="wellbeing",
    ).insert()

    # Catalog has no spending data -- this finding shouldn't surface.
    catalog = {
        "metrics.daily_outcomes": {"columns": [{"name": "mood", "category": "wellbeing"}]},
    }
    suggestions = suggest_hypotheses(catalog, limit=10)
    assert len(suggestions) == 0


def test_for_question():
    from app.literature import Finding

    _make_finding(
        exposure="sleep_quality",
        outcome="heart_rate_variability",
        exposure_categories="sleep",
        outcome_categories="cardiovascular",
    ).insert()

    catalog = {
        "metrics.daily_hrv": {"columns": [{"name": "rmssd", "category": "cardiovascular"}]},
        "metrics.daily_sleep": {"columns": [{"name": "score", "category": "sleep"}]},
    }
    results = Finding.for_question("does sleep affect HRV?", catalog)
    assert len(results) == 1


def test_delete_finding():
    f = _make_finding()
    f.insert()
    fid = f.id
    f.delete()
    assert type(f).find(fid) is None
