"""Tests for app.literature_fetch -- API clients, extraction, refresh."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

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


# ------------------------------------------------------------------
# OpenAlex
# ------------------------------------------------------------------


def test_reconstruct_abstract():
    from app.literature_fetch import _reconstruct_abstract

    inverted = {"Hello": [0], "world": [1], "of": [2], "science": [3]}
    assert _reconstruct_abstract(inverted) == "Hello world of science"


def test_reconstruct_abstract_none():
    from app.literature_fetch import _reconstruct_abstract

    assert _reconstruct_abstract(None) == ""


def test_search_openalex_success():
    from app.literature_fetch import search_openalex

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": "https://openalex.org/W1234",
                "title": "Sleep and HRV: A Meta-Analysis",
                "abstract_inverted_index": {"Sleep": [0], "affects": [1], "HRV": [2]},
                "doi": "10.1234/test",
                "cited_by_count": 200,
                "publication_year": 2023,
                "type": "review",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.literature_fetch.httpx.get", return_value=mock_response):
        results = search_openalex("sleep heart rate variability")

    assert len(results) == 1
    assert results[0].title == "Sleep and HRV: A Meta-Analysis"
    assert results[0].abstract == "Sleep affects HRV"
    assert results[0].openalex_id == "https://openalex.org/W1234"


def test_search_openalex_filters_no_abstract():
    from app.literature_fetch import search_openalex

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": "W1",
                "title": "No abstract paper",
                "abstract_inverted_index": None,
                "doi": None,
                "cited_by_count": 100,
                "publication_year": 2022,
                "type": "article",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.literature_fetch.httpx.get", return_value=mock_response):
        results = search_openalex("test")
    assert len(results) == 0


# ------------------------------------------------------------------
# Semantic Scholar
# ------------------------------------------------------------------


def test_search_semantic_scholar_success():
    from app.literature_fetch import search_semantic_scholar

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Exercise and mood",
                "abstract": "Exercise improves mood significantly.",
                "tldr": {"text": "Exercise improves mood."},
                "externalIds": {"DOI": "10.5678/test"},
                "citationCount": 150,
                "year": 2022,
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.literature_fetch.httpx.get", return_value=mock_response):
        results = search_semantic_scholar("exercise mood")

    assert len(results) == 1
    assert results[0].title == "Exercise and mood"
    assert results[0].doi == "10.5678/test"


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
# Refresh (integration-ish, with mocked APIs)
# ------------------------------------------------------------------


def test_refresh_findings():
    from app.literature import Finding
    from app.literature_fetch import OpenAlexPaper, refresh_findings

    mock_papers = [
        OpenAlexPaper(
            openalex_id="W001",
            title="Sleep and HRV",
            abstract="Sleep affects HRV significantly.",
            doi="10.1/test",
            citation_count=100,
            publication_year=2023,
            type="review",
        )
    ]

    provider = MagicMock()
    provider.ask.return_value = {
        "exposure": "sleep_quality",
        "outcome": "heart_rate_variability",
        "direction": "positive",
        "effect_size": 0.4,
        "effect_size_type": "r",
        "evidence_level": "meta_analysis",
        "exposure_categories": "sleep",
        "outcome_categories": "cardiovascular",
        "skip": False,
    }

    catalog = {
        "metrics.daily_hrv": {"columns": [{"name": "rmssd", "category": "cardiovascular"}]},
        "metrics.daily_sleep": {"columns": [{"name": "score", "category": "sleep"}]},
    }

    with patch("app.literature_fetch.search_openalex", return_value=mock_papers):
        stats = refresh_findings(catalog, provider, papers_per_pair=1)

    assert stats["findings_extracted"] >= 1
    all_findings = Finding.all()
    assert len(all_findings) >= 1
    assert all_findings[0].openalex_id == "W001"


def test_refresh_findings_dedup():
    from app.literature import Finding
    from app.literature_fetch import refresh_findings

    # Pre-insert a finding with the same openalex_id
    Finding(
        exposure="sleep",
        outcome="hrv",
        direction="positive",
        evidence_level="rct",
        exposure_categories="sleep",
        outcome_categories="cardiovascular",
        openalex_id="W001",
        citation="existing",
    ).insert()

    from app.literature_fetch import OpenAlexPaper

    mock_papers = [
        OpenAlexPaper(
            openalex_id="W001",
            title="Sleep and HRV",
            abstract="Duplicate paper.",
            doi="",
            citation_count=50,
            publication_year=2023,
            type="review",
        )
    ]

    provider = MagicMock()
    catalog = {
        "metrics.daily_hrv": {"columns": [{"name": "rmssd", "category": "cardiovascular"}]},
        "metrics.daily_sleep": {"columns": [{"name": "score", "category": "sleep"}]},
    }

    with patch("app.literature_fetch.search_openalex", return_value=mock_papers):
        stats = refresh_findings(catalog, provider, papers_per_pair=1)

    assert stats["duplicates"] >= 1
    # Should still have only the original finding
    all_findings = Finding.all()
    assert len(all_findings) == 1
