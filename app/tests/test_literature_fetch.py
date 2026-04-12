"""Tests for app.literature_fetch -- LLM extraction, category helpers, gateway refresh."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

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
    con.execute("CREATE SCHEMA IF NOT EXISTS shenas_system")

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


# ------------------------------------------------------------------
# LLM extraction
# ------------------------------------------------------------------


def test_extract_finding_from_abstract():
    from app.literature_fetch import extract_finding_from_abstract

    provider = MagicMock()
    provider.ask.return_value = {
        "exposure": "sleep_duration",
        "outcome": "cognitive_performance",
        "direction": "positive",
        "effect_size": 0.35,
        "effect_size_type": "r",
        "lag_hours": 8.0,
        "lag_max_hours": 16.0,
        "evidence_level": "rct",
        "sample_size": 200,
        "population": "healthy_adults",
        "mechanism": "Sleep consolidates memory",
        "exposure_categories": "sleep",
        "outcome_categories": "performance",
        "skip": False,
    }

    result = extract_finding_from_abstract(
        provider,
        title="Sleep and cognition",
        abstract="Sleep improves cognitive performance...",
        citation="Jones et al., 2022",
    )

    assert result is not None
    assert result.exposure == "sleep_duration"
    assert result.outcome == "cognitive_performance"
    assert result.direction == "positive"
    assert result.effect_size == 0.35


def test_extract_finding_skip():
    from app.literature_fetch import extract_finding_from_abstract

    provider = MagicMock()
    provider.ask.return_value = {
        "skip": True,
        "exposure": "x",
        "outcome": "y",
        "direction": "null",
        "evidence_level": "cross_sectional",
        "exposure_categories": "",
        "outcome_categories": "",
    }

    result = extract_finding_from_abstract(provider, title="Irrelevant", abstract="Not useful")
    assert result is None


def test_extract_finding_llm_failure():
    from app.literature_fetch import extract_finding_from_abstract

    provider = MagicMock()
    provider.ask.side_effect = RuntimeError("LLM down")

    result = extract_finding_from_abstract(provider, title="Test", abstract="Test")
    assert result is None


# ------------------------------------------------------------------
# Category pairs
# ------------------------------------------------------------------


def test_category_search_pairs():
    from app.literature_fetch import category_search_pairs

    pairs = category_search_pairs({"sleep", "cardiovascular", "activity"})
    # activity-cardiovascular, activity-sleep, cardiovascular-sleep
    assert len(pairs) == 3
    assert ("activity", "cardiovascular") in pairs
    assert ("activity", "sleep") in pairs
    assert ("cardiovascular", "sleep") in pairs


def test_category_search_pairs_filters_empty_terms():
    from app.literature_fetch import category_search_pairs

    # "time" has empty search terms, should be excluded
    pairs = category_search_pairs({"sleep", "time"})
    assert len(pairs) == 0


def test_build_search_query():
    from app.literature_fetch import build_search_query

    q = build_search_query("sleep", "cardiovascular")
    assert "sleep" in q.lower()
    assert "heart rate variability" in q.lower()


# ------------------------------------------------------------------
# Paper model
# ------------------------------------------------------------------


def test_paper_model():
    from app.literature_fetch import Paper

    p = Paper(
        source_ref="W1234",
        title="Sleep and HRV",
        abstract="Sleep affects HRV significantly.",
        doi="10.1234/test",
        citation_count=200,
        publication_year=2023,
    )
    assert p.source_ref == "W1234"
    assert p.title == "Sleep and HRV"


# ------------------------------------------------------------------
# Gateway refresh
# ------------------------------------------------------------------


def test_refresh_findings_no_token():
    """refresh_findings raises when there is no remote token."""
    from app.literature_fetch import refresh_findings

    catalog = {
        "metrics.daily_hrv": {"columns": [{"name": "rmssd", "category": "cardiovascular"}]},
        "metrics.daily_sleep": {"columns": [{"name": "score", "category": "sleep"}]},
    }

    with (
        patch("app.local_users.LocalUser.get_remote_token", return_value=None),
        pytest.raises(RuntimeError, match=r"shenas\.net account"),
    ):
        refresh_findings(catalog)


def test_refresh_findings_success():
    from app.finding import Finding
    from app.literature_fetch import refresh_findings

    gateway_response = {
        "stats": {"pairs": 1, "papers_fetched": 1, "findings_extracted": 1, "skipped": 0, "duplicates": 0},
        "findings": [
            {
                "exposure": "sleep_quality",
                "outcome": "heart_rate_variability",
                "direction": "positive",
                "effect_size": 0.4,
                "effect_size_type": "r",
                "evidence_level": "meta_analysis",
                "citation": "Smith et al., 2023",
                "doi": "10.1/test",
                "source_kind": "academic",
                "exposure_categories": "sleep",
                "outcome_categories": "cardiovascular",
                "source_ref": "W001",
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(gateway_response).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.local_users.LocalUser.get_remote_token", return_value="tok_123"),
        patch("app.literature_fetch.urllib.request.urlopen", return_value=mock_resp),
    ):
        stats = refresh_findings(
            {
                "metrics.daily_hrv": {"columns": [{"name": "rmssd", "category": "cardiovascular"}]},
                "metrics.daily_sleep": {"columns": [{"name": "score", "category": "sleep"}]},
            }
        )

    assert stats["findings_extracted"] == 1
    all_findings = Finding.all()
    assert len(all_findings) >= 1
    assert all_findings[0].source_ref == "W001"


def test_refresh_findings_empty_categories():
    from app.literature_fetch import refresh_findings

    stats = refresh_findings({})
    assert stats["papers_fetched"] == 0
