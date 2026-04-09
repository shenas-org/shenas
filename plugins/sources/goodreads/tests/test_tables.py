from unittest.mock import MagicMock

from shenas_sources.goodreads.client import GoodreadsClient
from shenas_sources.goodreads.tables import Books, Readings, Shelves

SAMPLE_ENTRY = {
    "book_id": "12345",
    "title": "The Great Gatsby",
    "author_name": "F. Scott Fitzgerald",
    "isbn": "0743273567",
    "book": {"num_pages": "180"},
    "book_published": "1925",
    "average_rating": "3.93",
    "user_rating": "5",
    "user_read_at": "Sun, 15 Mar 2026 00:00:00 +0000",
    "user_date_added": "Sat, 10 Jan 2026 12:00:00 +0000",
    "user_shelves": "read, fiction, classics",
    "_shelf": "read",
    "user_review": "A timeless classic",
}

SAMPLE_TO_READ = {
    "book_id": "67890",
    "title": "Dune",
    "author_name": "Frank Herbert",
    "isbn": "0441172717",
    "book": {"num_pages": "688"},
    "book_published": "1965",
    "average_rating": "4.25",
    "user_rating": "0",
    "user_read_at": "",
    "user_date_added": "Sat, 20 Feb 2026 00:00:00 +0000",
    "user_shelves": "to-read",
    "_shelf": "to-read",
    "user_review": "",
}


class TestParseEntry:
    def test_parses_complete_entry(self) -> None:
        parsed = GoodreadsClient.parse_entry(SAMPLE_ENTRY)
        assert parsed["book_id"] == "12345"
        assert parsed["title"] == "The Great Gatsby"
        assert parsed["author"] == "F. Scott Fitzgerald"
        assert parsed["isbn"] == "0743273567"
        assert parsed["num_pages"] == 180
        assert parsed["year_published"] == 1925
        assert parsed["average_rating"] == 3.93
        assert parsed["my_rating"] == 5
        assert parsed["date_read"] == "2026-03-15"
        assert parsed["date_added"] == "2026-01-10"
        assert parsed["exclusive_shelf"] == "read"
        assert parsed["my_review"] == "A timeless classic"

    def test_parses_to_read_entry(self) -> None:
        parsed = GoodreadsClient.parse_entry(SAMPLE_TO_READ)
        assert parsed["book_id"] == "67890"
        assert parsed["date_read"] is None
        assert parsed["my_rating"] == 0
        assert parsed["exclusive_shelf"] == "to-read"


class TestBooks:
    def test_extract_yields_book_metadata(self) -> None:
        client = MagicMock()
        rows = list(Books.extract(client, entries=[SAMPLE_ENTRY]))
        assert len(rows) == 1
        assert rows[0]["book_id"] == "12345"
        assert rows[0]["title"] == "The Great Gatsby"
        assert rows[0]["author"] == "F. Scott Fitzgerald"
        assert rows[0]["num_pages"] == 180
        assert rows[0]["year_published"] == 1925

    def test_extract_multiple_books(self) -> None:
        client = MagicMock()
        rows = list(Books.extract(client, entries=[SAMPLE_ENTRY, SAMPLE_TO_READ]))
        assert len(rows) == 2

    def test_extract_empty(self) -> None:
        client = MagicMock()
        assert list(Books.extract(client, entries=[])) == []


class TestReadings:
    def test_extract_yields_only_read_books(self) -> None:
        client = MagicMock()
        rows = list(Readings.extract(client, entries=[SAMPLE_ENTRY, SAMPLE_TO_READ]))
        assert len(rows) == 1
        assert rows[0]["book_id"] == "12345"
        assert rows[0]["date_read"] == "2026-03-15"
        assert rows[0]["my_rating"] == 5
        assert rows[0]["exclusive_shelf"] == "read"

    def test_extract_skips_to_read(self) -> None:
        client = MagicMock()
        rows = list(Readings.extract(client, entries=[SAMPLE_TO_READ]))
        assert rows == []


class TestShelves:
    def test_extract_yields_all_books(self) -> None:
        client = MagicMock()
        rows = list(Shelves.extract(client, entries=[SAMPLE_ENTRY, SAMPLE_TO_READ]))
        assert len(rows) == 2
        shelves = {r["book_id"]: r["exclusive_shelf"] for r in rows}
        assert shelves["12345"] == "read"
        assert shelves["67890"] == "to-read"

    def test_extract_captures_user_shelves(self) -> None:
        client = MagicMock()
        rows = list(Shelves.extract(client, entries=[SAMPLE_ENTRY]))
        assert rows[0]["user_shelves"] == "read, fiction, classics"
