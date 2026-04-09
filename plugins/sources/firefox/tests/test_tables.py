"""Tests for Firefox source tables."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from shenas_sources.firefox.tables import Bookmarks, Visits

if TYPE_CHECKING:
    from pathlib import Path


def _create_places_db(path: Path) -> str:
    """Create a minimal Firefox places.sqlite for testing."""
    db_path = str(path / "places.sqlite")
    con = sqlite3.connect(db_path)
    con.executescript("""
        CREATE TABLE moz_places (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            visit_count INTEGER DEFAULT 0,
            frecency INTEGER DEFAULT 0
        );
        CREATE TABLE moz_historyvisits (
            id INTEGER PRIMARY KEY,
            place_id INTEGER,
            visit_date INTEGER,
            visit_type INTEGER DEFAULT 1,
            from_visit INTEGER DEFAULT 0
        );
        CREATE TABLE moz_bookmarks (
            id INTEGER PRIMARY KEY,
            type INTEGER DEFAULT 1,
            fk INTEGER,
            parent INTEGER,
            title TEXT,
            dateAdded INTEGER
        );

        -- 2024-01-01 00:00:00 UTC = 1704067200 seconds = 1704067200000000 us
        INSERT INTO moz_places (id, url, title, visit_count)
        VALUES (1, 'https://example.com', 'Example', 3);

        INSERT INTO moz_places (id, url, title, visit_count)
        VALUES (2, 'https://mozilla.org', 'Mozilla', 1);

        INSERT INTO moz_historyvisits (id, place_id, visit_date, visit_type, from_visit)
        VALUES (1, 1, 1704067200000000, 2, 0);

        INSERT INTO moz_historyvisits (id, place_id, visit_date, visit_type, from_visit)
        VALUES (2, 2, 1704070800000000, 1, 1);

        -- Bookmark folders (type=2)
        INSERT INTO moz_bookmarks (id, type, fk, parent, title, dateAdded)
        VALUES (1, 2, NULL, 0, 'Bookmarks Toolbar', 1704067200000000);

        -- Bookmark items (type=1)
        INSERT INTO moz_bookmarks (id, type, fk, parent, title, dateAdded)
        VALUES (2, 1, 1, 1, 'Example Site', 1704067200000000);

        INSERT INTO moz_bookmarks (id, type, fk, parent, title, dateAdded)
        VALUES (3, 1, 2, 1, 'Mozilla', 1704070800000000);
    """)
    con.close()
    return db_path


def test_visits_extract(tmp_path: Path) -> None:
    db_path = _create_places_db(tmp_path)
    rows = list(Visits.extract(db_path))
    assert len(rows) == 2

    first = rows[0]
    assert first["id"] == 1
    assert first["url"] == "https://example.com"
    assert first["title"] == "Example"
    assert first["visit_type"] == "typed"
    assert first["visit_time"] is not None
    assert first["from_visit_id"] is None

    second = rows[1]
    assert second["id"] == 2
    assert second["visit_type"] == "link"
    assert second["from_visit_id"] == 1


def test_bookmarks_extract(tmp_path: Path) -> None:
    db_path = _create_places_db(tmp_path)
    rows = list(Bookmarks.extract(db_path))
    assert len(rows) == 2

    assert rows[0]["title"] == "Example Site"
    assert rows[0]["url"] == "https://example.com"
    assert rows[0]["parent_title"] == "Bookmarks Toolbar"
    assert rows[0]["date_added"] is not None

    assert rows[1]["title"] == "Mozilla"
    assert rows[1]["url"] == "https://mozilla.org"
