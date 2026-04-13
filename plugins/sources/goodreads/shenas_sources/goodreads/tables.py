"""Goodreads source tables (RSS feed scraping).

Data is fetched from public Goodreads RSS feeds. The ``entries``
context kwarg carries the pre-fetched list of parsed feed entries
(shared across all tables from a single ``get_all_shelves()`` call).

- ``Books`` is a ``DimensionTable`` (SCD2) keyed on ``book_id``.
- ``Readings`` is an ``EventTable`` keyed on (``book_id``, ``date_read``).
  Only entries with a non-empty date_read are yielded.
- ``Shelves`` is a ``SnapshotTable`` (SCD2) keyed on ``book_id``.
  SCD2 tracks when books move between shelves across syncs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import (
    DimensionTable,
    EventTable,
    SnapshotTable,
    SourceTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class Books(DimensionTable):
    """Book metadata from Goodreads. SCD2 captures changes across syncs."""

    class _Meta:
        name = "books"
        display_name = "Books"
        description = "Book metadata scraped from Goodreads RSS feeds."
        pk = ("book_id",)

    book_id: Annotated[str, Field(db_type="VARCHAR", description="Goodreads Book ID", display_name="Book ID")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Book title", display_name="Title")] = None
    author: Annotated[str | None, Field(db_type="VARCHAR", description="Primary author", display_name="Author")] = None
    isbn: Annotated[str | None, Field(db_type="VARCHAR", description="ISBN", display_name="ISBN")] = None
    num_pages: Annotated[int | None, Field(db_type="INTEGER", description="Number of pages", display_name="Page Count")] = None
    year_published: Annotated[
        int | None, Field(db_type="INTEGER", description="Year published", display_name="Year Published")
    ] = None
    average_rating: Annotated[
        float | None, Field(db_type="DOUBLE", description="Goodreads average rating", display_name="Average Rating")
    ] = None

    @classmethod
    def extract(cls, client: Any, *, entries: list[dict[str, Any]] | None = None, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG003
        from shenas_sources.goodreads.client import GoodreadsClient

        for entry in entries or []:
            parsed = GoodreadsClient.parse_entry(entry)
            if not parsed["book_id"]:
                continue
            yield {
                "book_id": parsed["book_id"],
                "title": parsed["title"],
                "author": parsed["author"],
                "isbn": parsed["isbn"],
                "num_pages": parsed["num_pages"],
                "year_published": parsed["year_published"],
                "average_rating": parsed["average_rating"],
            }


class Readings(EventTable):
    """Books read with completion date and rating.

    Only entries with a non-empty date_read are yielded -- books on the
    to-read or currently-reading shelf without a read date are skipped.
    """

    class _Meta:
        name = "readings"
        display_name = "Readings"
        description = "Books marked as read with completion date and personal rating."
        pk = ("book_id", "date_read")

    time_at: ClassVar[str] = "date_read"

    book_id: Annotated[str, Field(db_type="VARCHAR", description="Goodreads Book ID", display_name="Book ID")]
    date_read: Annotated[
        str | None, Field(db_type="DATE", description="Date the book was finished", display_name="Date Read")
    ] = None
    date_added: Annotated[
        str | None, Field(db_type="DATE", description="Date added to Goodreads", display_name="Date Added")
    ] = None
    my_rating: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Personal rating", display_name="My Rating", value_range=(0, 5)),
    ] = None
    exclusive_shelf: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Shelf (read, currently-reading, to-read)", display_name="Shelf"),
    ] = None
    my_review: Annotated[
        str | None, Field(db_type="VARCHAR", description="Personal review text", display_name="My Review")
    ] = None

    @classmethod
    def extract(cls, client: Any, *, entries: list[dict[str, Any]] | None = None, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG003
        from shenas_sources.goodreads.client import GoodreadsClient

        for entry in entries or []:
            parsed = GoodreadsClient.parse_entry(entry)
            if not parsed["book_id"] or not parsed["date_read"]:
                continue
            yield {
                "book_id": parsed["book_id"],
                "date_read": parsed["date_read"],
                "date_added": parsed["date_added"],
                "my_rating": parsed["my_rating"],
                "exclusive_shelf": parsed["exclusive_shelf"],
                "my_review": parsed["my_review"],
            }


class Shelves(SnapshotTable):
    """Current shelf assignment per book. SCD2 captures shelf changes across syncs."""

    class _Meta:
        name = "shelves"
        display_name = "Shelves"
        description = "Current shelf assignment for each book."
        pk = ("book_id",)

    book_id: Annotated[str, Field(db_type="VARCHAR", description="Goodreads Book ID", display_name="Book ID")]
    exclusive_shelf: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Exclusive shelf (read, currently-reading, to-read)", display_name="Shelf"),
    ] = None
    user_shelves: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="All shelves (comma-separated, includes custom)", display_name="User Shelves"),
    ] = None

    @classmethod
    def extract(cls, client: Any, *, entries: list[dict[str, Any]] | None = None, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG003
        from shenas_sources.goodreads.client import GoodreadsClient

        for entry in entries or []:
            parsed = GoodreadsClient.parse_entry(entry)
            if not parsed["book_id"]:
                continue
            yield {
                "book_id": parsed["book_id"],
                "exclusive_shelf": parsed["exclusive_shelf"],
                "user_shelves": parsed["user_shelves"],
            }


TABLES: tuple[type[SourceTable], ...] = (Books, Readings, Shelves)
