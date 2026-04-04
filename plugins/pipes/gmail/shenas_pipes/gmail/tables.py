"""Gmail raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field


@dataclass
class Message:
    """Gmail message metadata."""

    __table__: ClassVar[str] = "messages"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Message ID")]
    thread_id: Annotated[str | None, Field(db_type="VARCHAR", description="Thread ID")] = None
    internal_date: Annotated[int, Field(db_type="BIGINT", description="Internal date as epoch milliseconds")] = 0
    date: Annotated[str | None, Field(db_type="VARCHAR", description="Date header value")] = None
    from_address: Annotated[str | None, Field(db_type="VARCHAR", description="From address")] = None
    to_address: Annotated[str | None, Field(db_type="VARCHAR", description="To address")] = None
    subject: Annotated[str | None, Field(db_type="VARCHAR", description="Subject line")] = None
    snippet: Annotated[str | None, Field(db_type="TEXT", description="Message snippet")] = None
    labels: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated label IDs")] = None
    size_estimate: Annotated[int, Field(db_type="INTEGER", description="Estimated message size in bytes")] = 0


@dataclass
class Label:
    """Gmail label."""

    __table__: ClassVar[str] = "labels"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Label ID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Label name")] = None
    type: Annotated[str | None, Field(db_type="VARCHAR", description="Label type (system or user)")] = None
