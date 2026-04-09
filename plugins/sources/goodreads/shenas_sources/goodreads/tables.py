"""Goodreads source tables (CSV export import).

Goodreads shut down its API in 2020. This source reads from the CSV
export available at https://www.goodreads.com/review/import.

- ``Books`` is a ``DimensionTable`` (SCD2) keyed on ``book_id``.
  Captures metadata updates if the user re-exports after edits.
- ``Readings`` is an ``EventTable`` keyed on (``book_id``, ``date_read``).
  Only rows with a non-empty ``Date Read`` column are yielded.
- ``Shelves`` is a ``SnapshotTable`` (SCD2) keyed on ``book_id``.
  SCD2 tracks when books move between shelves across re-imports.
"""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.table import Field
from shenas_sources.core.table import (
    DimensionTable,
    EventTable,
    SnapshotTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


def _strip_isbn(raw: str | None) -> str | None:
    """Strip the ``="..."`` wrapper Goodreads puts around ISBN fields."""
    if not raw:
        return None
    return raw.strip().strip('="').strip('"').strip() or None


def _int_or_none(raw: str | None) -> int | None:
    if not raw or not raw.strip():
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def _float_or_none(raw: str | None) -> float | None:
    if not raw or not raw.strip():
        return None
    try:
        return float(raw.strip())
    except ValueError:
        return None


def _read_csv(csv_path: Any) -> list[dict[str, str]]:
    """Read the Goodreads CSV export into a list of dicts."""
    with open(csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class Books(DimensionTable):
    """Book metadata from the Goodreads library. SCD2 captures edits across re-imports."""

    class _Meta:
        name = "books"
        display_name = "Books"
        description = "Book metadata from Goodreads CSV export."
        pk = ("book_id",)

    book_id: Annotated[str, Field(db_type="VARCHAR", description="Goodreads Book ID")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Book title")] = None
    author: Annotated[str | None, Field(db_type="VARCHAR", description="Primary author")] = None
    additional_authors: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Additional authors (comma-separated)"),
    ] = None
    isbn: Annotated[str | None, Field(db_type="VARCHAR", description="ISBN-10")] = None
    isbn13: Annotated[str | None, Field(db_type="VARCHAR", description="ISBN-13")] = None
    num_pages: Annotated[int | None, Field(db_type="INTEGER", description="Number of pages")] = None
    year_published: Annotated[int | None, Field(db_type="INTEGER", description="Year published")] = None
    publisher: Annotated[str | None, Field(db_type="VARCHAR", description="Publisher")] = None
    average_rating: Annotated[float | None, Field(db_type="DOUBLE", description="Goodreads average rating")] = None
    binding: Annotated[str | None, Field(db_type="VARCHAR", description="Binding (Hardcover, Paperback, etc.)")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        for row in _read_csv(client):
            book_id = row.get("Book Id", "").strip()
            if not book_id:
                continue
            yield {
                "book_id": book_id,
                "title": row.get("Title", "").strip() or None,
                "author": row.get("Author", "").strip() or None,
                "additional_authors": row.get("Additional Authors", "").strip() or None,
                "isbn": _strip_isbn(row.get("ISBN")),
                "isbn13": _strip_isbn(row.get("ISBN13")),
                "num_pages": _int_or_none(row.get("Number of Pages")),
                "year_published": _int_or_none(row.get("Year Published")),
                "publisher": row.get("Publisher", "").strip() or None,
                "average_rating": _float_or_none(row.get("Average Rating")),
                "binding": row.get("Binding", "").strip() or None,
            }


class Readings(EventTable):
    """Books read with completion date and rating.

    Only rows with a non-empty ``Date Read`` are yielded -- books on the
    to-read or currently-reading shelf without a read date are skipped.
    """

    class _Meta:
        name = "readings"
        display_name = "Readings"
        description = "Books marked as read with completion date and personal rating."
        pk = ("book_id", "date_read")

    time_at: ClassVar[str] = "date_read"

    book_id: Annotated[str, Field(db_type="VARCHAR", description="Goodreads Book ID")]
    date_read: Annotated[str | None, Field(db_type="DATE", description="Date the book was finished")] = None
    date_added: Annotated[str | None, Field(db_type="DATE", description="Date added to Goodreads")] = None
    my_rating: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Personal rating", value_range=(0, 5)),
    ] = None
    exclusive_shelf: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Shelf (read, currently-reading, to-read)"),
    ] = None
    my_review: Annotated[str | None, Field(db_type="VARCHAR", description="Personal review text")] = None
    read_count: Annotated[int | None, Field(db_type="INTEGER", description="Number of times read")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        for row in _read_csv(client):
            book_id = row.get("Book Id", "").strip()
            date_read = row.get("Date Read", "").strip()
            if not book_id or not date_read:
                continue
            yield {
                "book_id": book_id,
                "date_read": date_read,
                "date_added": row.get("Date Added", "").strip() or None,
                "my_rating": _int_or_none(row.get("My Rating")),
                "exclusive_shelf": row.get("Exclusive Shelf", "").strip() or None,
                "my_review": row.get("My Review", "").strip() or None,
                "read_count": _int_or_none(row.get("Read Count")),
            }


class Shelves(SnapshotTable):
    """Current shelf assignment per book. SCD2 captures shelf changes across re-imports."""

    class _Meta:
        name = "shelves"
        display_name = "Shelves"
        description = "Current shelf assignment for each book."
        pk = ("book_id",)

    book_id: Annotated[str, Field(db_type="VARCHAR", description="Goodreads Book ID")]
    exclusive_shelf: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Exclusive shelf (read, currently-reading, to-read)"),
    ] = None
    bookshelves: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Custom shelves (comma-separated)"),
    ] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        for row in _read_csv(client):
            book_id = row.get("Book Id", "").strip()
            if not book_id:
                continue
            yield {
                "book_id": book_id,
                "exclusive_shelf": row.get("Exclusive Shelf", "").strip() or None,
                "bookshelves": row.get("Bookshelves", "").strip() or None,
            }


TABLES: tuple[type, ...] = (Books, Readings, Shelves)
