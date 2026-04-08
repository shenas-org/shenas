"""Google Takeout source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. Photos / location / YouTube history are
all ``EventTable`` (point-in-time records). YouTube subscriptions become
``SnapshotTable`` (SCD2) so an unsubscribe closes the row instead of
silently erasing history.

Each table's ``extract`` method takes the extracted-Takeout-archive
``Path`` as its client argument and pulls files via the parser modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.field import Field
from shenas_sources.core.table import (
    EventTable,
    SnapshotTable,
)
from shenas_sources.gtakeout.drive import iter_files
from shenas_sources.gtakeout.parsers.location import parse_location_records, parse_semantic_locations
from shenas_sources.gtakeout.parsers.photos import parse_photos_metadata
from shenas_sources.gtakeout.parsers.youtube import parse_search_history, parse_subscriptions, parse_watch_history

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class PhotosMetadata(EventTable):
    """Google Photos metadata from Takeout."""

    name: ClassVar[str] = "photos_metadata"
    display_name: ClassVar[str] = "Photos Metadata"
    description: ClassVar[str | None] = "Per-photo metadata extracted from Google Photos Takeout."
    pk: ClassVar[tuple[str, ...]] = ("title", "photo_taken_timestamp")
    time_at: ClassVar[str] = "photo_taken_timestamp"

    title: Annotated[str, Field(db_type="VARCHAR", description="Photo/video title")] = ""
    photo_taken_timestamp: Annotated[str, Field(db_type="VARCHAR", description="Epoch timestamp when photo was taken")] = ""
    photo_description: Annotated[str | None, Field(db_type="TEXT", description="Photo description")] = None
    photo_taken_formatted: Annotated[str | None, Field(db_type="VARCHAR", description="Formatted photo taken date")] = None
    creation_timestamp: Annotated[str | None, Field(db_type="VARCHAR", description="Epoch creation timestamp")] = None
    creation_formatted: Annotated[str | None, Field(db_type="VARCHAR", description="Formatted creation date")] = None
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude")] = 0.0
    altitude: Annotated[float, Field(db_type="DOUBLE", description="Altitude")] = 0.0
    latitude_exif: Annotated[float, Field(db_type="DOUBLE", description="EXIF latitude")] = 0.0
    longitude_exif: Annotated[float, Field(db_type="DOUBLE", description="EXIF longitude")] = 0.0
    camera_make: Annotated[str | None, Field(db_type="VARCHAR", description="Camera/device type")] = None
    url: Annotated[str | None, Field(db_type="VARCHAR", description="Photo URL")] = None
    source_file: Annotated[str | None, Field(db_type="VARCHAR", description="Source JSON filename")] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "Google Photos")
        yield from parse_photos_metadata(files)


class LocationRecords(EventTable):
    """Raw location record from Location History."""

    name: ClassVar[str] = "location_records"
    display_name: ClassVar[str] = "Location Records"
    description: ClassVar[str | None] = "Raw location pings from Location History."
    pk: ClassVar[tuple[str, ...]] = ("timestamp", "latitude", "longitude")
    time_at: ClassVar[str] = "timestamp"

    timestamp: Annotated[str, Field(db_type="VARCHAR", description="ISO timestamp")] = ""
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude")] = 0.0
    accuracy: Annotated[int, Field(db_type="INTEGER", description="Accuracy in meters")] = 0
    altitude: Annotated[int, Field(db_type="INTEGER", description="Altitude in meters")] = 0
    source: Annotated[str | None, Field(db_type="VARCHAR", description="Location source")] = None
    device_tag: Annotated[str | None, Field(db_type="VARCHAR", description="Device identifier")] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "Location History (Timeline)")
        if not files:
            files = iter_files(client, "Location History")
        yield from parse_location_records(files)


class LocationVisits(EventTable):
    """Semantic location visit or activity segment."""

    name: ClassVar[str] = "location_visits"
    display_name: ClassVar[str] = "Location Visits"
    description: ClassVar[str | None] = "Semantic place visits / activity segments."
    pk: ClassVar[tuple[str, ...]] = ("start_timestamp", "place_name", "type")
    time_at: ClassVar[str] = "start_timestamp"

    start_timestamp: Annotated[str, Field(db_type="VARCHAR", description="Start ISO timestamp")] = ""
    place_name: Annotated[str, Field(db_type="VARCHAR", description="Place name or activity type")] = ""
    type: Annotated[str, Field(db_type="VARCHAR", description="Entry type: visit or activity")] = ""
    place_address: Annotated[str | None, Field(db_type="VARCHAR", description="Place address")] = None
    place_id: Annotated[str | None, Field(db_type="VARCHAR", description="Google place ID")] = None
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude")] = 0.0
    end_timestamp: Annotated[str | None, Field(db_type="VARCHAR", description="End ISO timestamp")] = None
    confidence: Annotated[str | None, Field(db_type="VARCHAR", description="Confidence level")] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "Location History (Timeline)/Semantic Location History")
        if not files:
            files = iter_files(client, "Location History/Semantic Location History")
        yield from parse_semantic_locations(files)


class YouTubeWatchHistory(EventTable):
    """YouTube watch history entry."""

    name: ClassVar[str] = "youtube_watch_history"
    display_name: ClassVar[str] = "YouTube Watch History"
    description: ClassVar[str | None] = "YouTube watch history events."
    pk: ClassVar[tuple[str, ...]] = ("title_url", "time")
    time_at: ClassVar[str] = "time"

    title_url: Annotated[str, Field(db_type="VARCHAR", description="Video URL")] = ""
    time: Annotated[str, Field(db_type="VARCHAR", description="Watch timestamp")] = ""
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Video title")] = None
    channel_name: Annotated[str | None, Field(db_type="VARCHAR", description="Channel name")] = None
    channel_url: Annotated[str | None, Field(db_type="VARCHAR", description="Channel URL")] = None
    product: Annotated[str | None, Field(db_type="VARCHAR", description="Product (YouTube or YouTube Music)")] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "YouTube and YouTube Music/history")
        yield from parse_watch_history(files)


class YouTubeSearchHistory(EventTable):
    """YouTube search history entry."""

    name: ClassVar[str] = "youtube_search_history"
    display_name: ClassVar[str] = "YouTube Search History"
    description: ClassVar[str | None] = "YouTube search history events."
    pk: ClassVar[tuple[str, ...]] = ("title", "time")
    time_at: ClassVar[str] = "time"

    title: Annotated[str, Field(db_type="VARCHAR", description="Search query")] = ""
    time: Annotated[str, Field(db_type="VARCHAR", description="Search timestamp")] = ""
    title_url: Annotated[str | None, Field(db_type="VARCHAR", description="Search URL")] = None
    product: Annotated[str | None, Field(db_type="VARCHAR", description="Product header")] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "YouTube and YouTube Music/history")
        yield from parse_search_history(files)


class YouTubeSubscriptions(SnapshotTable):
    """YouTube subscriptions. SCD2 closes a row when the user unsubscribes."""

    name: ClassVar[str] = "youtube_subscriptions"
    display_name: ClassVar[str] = "YouTube Subscriptions"
    description: ClassVar[str | None] = "Channels the user is subscribed to."
    pk: ClassVar[tuple[str, ...]] = ("channel_id",)

    channel_id: Annotated[str, Field(db_type="VARCHAR", description="YouTube channel ID")] = ""
    channel_url: Annotated[str | None, Field(db_type="VARCHAR", description="Channel URL")] = None
    channel_title: Annotated[str | None, Field(db_type="VARCHAR", description="Channel title")] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "YouTube and YouTube Music/subscriptions", suffix=".csv")
        yield from parse_subscriptions(files)


TABLES: tuple[type, ...] = (
    PhotosMetadata,
    LocationRecords,
    LocationVisits,
    YouTubeWatchHistory,
    YouTubeSearchHistory,
    YouTubeSubscriptions,
)
