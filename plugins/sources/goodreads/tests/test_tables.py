import tempfile
from pathlib import Path

from shenas_sources.goodreads.tables import Books, Readings, Shelves, _strip_isbn

CSV_HEADER = (
    "Book Id,Title,Author,Author l-f,Additional Authors,ISBN,ISBN13,"
    "My Rating,Average Rating,Publisher,Binding,Number of Pages,"
    "Year Published,Original Publication Year,Date Read,Date Added,"
    "Bookshelves,Bookshelves with positions,Exclusive Shelf,My Review,"
    "Spoiler,Private Notes,Read Count,Owned Copies\n"
)

ROW_READ = (
    '12345,The Great Gatsby,F. Scott Fitzgerald,"Fitzgerald, F. Scott",,'
    '="0743273567",="9780743273565",5,3.93,Scribner,Paperback,180,'
    "1925,1925,2026/03/15,2026/01/10,fiction classics,,read,"
    "A timeless classic,,private note,1,0\n"
)

ROW_TO_READ = (
    '67890,Dune,Frank Herbert,"Herbert, Frank",,="0441172717",="9780441172719",'
    "0,4.25,Ace Books,Paperback,688,1990,1965,,2026/02/20,sci-fi,,to-read,,,,0,0\n"
)


def _write_csv(*rows: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(CSV_HEADER)
        for r in rows:
            f.write(r)
    return Path(f.name)


class TestStripIsbn:
    def test_strips_wrapper(self) -> None:
        assert _strip_isbn('="0743273567"') == "0743273567"

    def test_none_input(self) -> None:
        assert _strip_isbn(None) is None

    def test_empty_string(self) -> None:
        assert _strip_isbn("") is None

    def test_plain_isbn(self) -> None:
        assert _strip_isbn("0743273567") == "0743273567"


class TestBooks:
    def test_extract_yields_book_metadata(self) -> None:
        csv_path = _write_csv(ROW_READ)
        rows = list(Books.extract(csv_path))
        assert len(rows) == 1
        assert rows[0]["book_id"] == "12345"
        assert rows[0]["title"] == "The Great Gatsby"
        assert rows[0]["author"] == "F. Scott Fitzgerald"
        assert rows[0]["isbn"] == "0743273567"
        assert rows[0]["num_pages"] == 180
        assert rows[0]["year_published"] == 1925

    def test_extract_multiple_books(self) -> None:
        csv_path = _write_csv(ROW_READ, ROW_TO_READ)
        rows = list(Books.extract(csv_path))
        assert len(rows) == 2


class TestReadings:
    def test_extract_yields_only_read_books(self) -> None:
        csv_path = _write_csv(ROW_READ, ROW_TO_READ)
        rows = list(Readings.extract(csv_path))
        # Only the read book has Date Read set
        assert len(rows) == 1
        assert rows[0]["book_id"] == "12345"
        assert rows[0]["date_read"] == "2026/03/15"
        assert rows[0]["my_rating"] == 5
        assert rows[0]["exclusive_shelf"] == "read"

    def test_extract_skips_to_read(self) -> None:
        csv_path = _write_csv(ROW_TO_READ)
        rows = list(Readings.extract(csv_path))
        assert rows == []


class TestShelves:
    def test_extract_yields_all_books(self) -> None:
        csv_path = _write_csv(ROW_READ, ROW_TO_READ)
        rows = list(Shelves.extract(csv_path))
        assert len(rows) == 2
        shelves = {r["book_id"]: r["exclusive_shelf"] for r in rows}
        assert shelves["12345"] == "read"
        assert shelves["67890"] == "to-read"

    def test_extract_captures_custom_shelves(self) -> None:
        csv_path = _write_csv(ROW_READ)
        rows = list(Shelves.extract(csv_path))
        assert rows[0]["bookshelves"] == "fiction classics"
