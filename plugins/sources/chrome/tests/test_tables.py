"""Tests for Chrome source tables."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from shenas_sources.chrome.tables import Downloads, SearchTerms, Visits


def _create_history_db(path: Path) -> str:
    """Create a minimal Chrome History database for testing."""
    db_path = str(path / "History")
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            visit_count INTEGER DEFAULT 0,
            typed_count INTEGER DEFAULT 0,
            last_visit_time INTEGER DEFAULT 0,
            hidden INTEGER DEFAULT 0
        );
        CREATE TABLE visits (
            id INTEGER PRIMARY KEY,
            url INTEGER NOT NULL,
            visit_time INTEGER NOT NULL,
            from_visit INTEGER DEFAULT 0,
            transition INTEGER DEFAULT 0,
            segment_id INTEGER DEFAULT 0,
            visit_duration INTEGER DEFAULT 0
        );
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY,
            guid TEXT,
            current_path TEXT,
            target_path TEXT,
            start_time INTEGER DEFAULT 0,
            received_bytes INTEGER DEFAULT 0,
            total_bytes INTEGER DEFAULT 0,
            state INTEGER DEFAULT 0,
            danger_type INTEGER DEFAULT 0,
            interrupt_reason INTEGER DEFAULT 0,
            hash BLOB,
            end_time INTEGER DEFAULT 0,
            opened INTEGER DEFAULT 0,
            last_access_time INTEGER DEFAULT 0,
            transient INTEGER DEFAULT 0,
            referrer TEXT,
            site_url TEXT,
            tab_url TEXT,
            tab_referrer_url TEXT,
            http_method TEXT,
            by_ext_id TEXT,
            by_ext_name TEXT,
            etag TEXT,
            last_modified TEXT,
            mime_type TEXT,
            original_mime_type TEXT
        );
        CREATE TABLE keyword_search_terms (
            keyword_id INTEGER NOT NULL,
            url_id INTEGER NOT NULL,
            term TEXT NOT NULL,
            normalized_term TEXT
        );

        -- Test data: 2026-01-15 12:00:00 UTC in Chrome epoch (microseconds since 1601-01-01)
        -- Unix timestamp: 1768483200, Chrome offset: 11644473600
        -- Chrome time: (1768483200 + 11644473600) * 1000000 = 13412956800000000
        INSERT INTO urls (id, url, title, visit_count, last_visit_time)
        VALUES (1, 'https://example.com', 'Example', 3, 13412956800000000);

        INSERT INTO urls (id, url, title, visit_count, last_visit_time)
        VALUES (2, 'https://www.google.com/search?q=test+query', 'test query - Google Search', 1, 13412956800000000);

        INSERT INTO visits (id, url, visit_time, from_visit, transition, visit_duration)
        VALUES (1, 1, 13412956800000000, 0, 1, 5000000);

        INSERT INTO visits (id, url, visit_time, from_visit, transition, visit_duration)
        VALUES (2, 1, 13412960400000000, 0, 0, 0);

        INSERT INTO downloads (id, tab_url, target_path, start_time, end_time,
            total_bytes, received_bytes, state, mime_type)
        VALUES (1, 'https://example.com/file.zip', '/tmp/file.zip',
            13412956800000000, 13412956860000000, 1024, 1024, 1, 'application/zip');

        INSERT INTO keyword_search_terms (keyword_id, url_id, term, normalized_term)
        VALUES (2, 2, 'test query', 'test query');
    """)
    con.close()
    return db_path


def test_visits_extract(tmp_path: Path) -> None:
    db_path = _create_history_db(tmp_path)
    rows = list(Visits.extract(db_path))
    assert len(rows) == 2

    first = rows[0]
    assert first["id"] == 1
    assert first["url"] == "https://example.com"
    assert first["title"] == "Example"
    assert first["transition"] == "typed"
    assert first["visit_duration_s"] == 5.0
    assert first["visit_time"] is not None

    second = rows[1]
    assert second["id"] == 2
    assert second["transition"] == "link"
    assert second["visit_duration_s"] is None  # 0 -> None


def test_downloads_extract(tmp_path: Path) -> None:
    db_path = _create_history_db(tmp_path)
    rows = list(Downloads.extract(db_path))
    assert len(rows) == 1

    row = rows[0]
    assert row["id"] == 1
    assert row["target_path"] == "/tmp/file.zip"
    assert row["total_bytes"] == 1024
    assert row["state"] == "complete"
    assert row["mime_type"] == "application/zip"
    assert row["start_time"] is not None
    assert row["end_time"] is not None


def test_search_terms_extract(tmp_path: Path) -> None:
    db_path = _create_history_db(tmp_path)
    rows = list(SearchTerms.extract(db_path))
    assert len(rows) == 1

    row = rows[0]
    assert row["url_id"] == 2
    assert row["term"] == "test query"
    assert row["normalized_term"] == "test query"
    assert row["url"] == "https://www.google.com/search?q=test+query"
    assert row["last_visit_time"] is not None
