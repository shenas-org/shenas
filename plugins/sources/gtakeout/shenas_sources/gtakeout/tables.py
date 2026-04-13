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

from app.table import Field
from shenas_sources.core.table import (
    EventTable,
    SnapshotTable,
    SourceTable,
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

    class _Meta:
        name = "photos_metadata"
        display_name = "Photos Metadata"
        description = "Per-photo metadata extracted from Google Photos Takeout."
        pk = ("title", "photo_taken_timestamp")

    time_at: ClassVar[str] = "photo_taken_timestamp"

    title: Annotated[str, Field(db_type="VARCHAR", description="Photo/video title", display_name="Title")] = ""
    photo_taken_timestamp: Annotated[
        str, Field(db_type="VARCHAR", description="Epoch timestamp when photo was taken", display_name="Photo Taken Time")
    ] = ""
    photo_description: Annotated[
        str | None, Field(db_type="TEXT", description="Photo description", display_name="Description")
    ] = None
    photo_taken_formatted: Annotated[
        str | None, Field(db_type="VARCHAR", description="Formatted photo taken date", display_name="Photo Taken Date")
    ] = None
    creation_timestamp: Annotated[
        str | None, Field(db_type="VARCHAR", description="Epoch creation timestamp", display_name="Creation Time")
    ] = None
    creation_formatted: Annotated[
        str | None, Field(db_type="VARCHAR", description="Formatted creation date", display_name="Creation Date")
    ] = None
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude", display_name="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude", display_name="Longitude")] = 0.0
    altitude: Annotated[float, Field(db_type="DOUBLE", description="Altitude", display_name="Altitude")] = 0.0
    latitude_exif: Annotated[float, Field(db_type="DOUBLE", description="EXIF latitude", display_name="EXIF Latitude")] = 0.0
    longitude_exif: Annotated[float, Field(db_type="DOUBLE", description="EXIF longitude", display_name="EXIF Longitude")] = (
        0.0
    )
    camera_make: Annotated[
        str | None, Field(db_type="VARCHAR", description="Camera/device type", display_name="Camera Make")
    ] = None
    url: Annotated[str | None, Field(db_type="VARCHAR", description="Photo URL", display_name="Photo URL")] = None
    source_file: Annotated[
        str | None, Field(db_type="VARCHAR", description="Source JSON filename", display_name="Source File")
    ] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "Google Photos")
        yield from parse_photos_metadata(files)


class LocationRecords(EventTable):
    """Raw location record from Location History."""

    class _Meta:
        name = "location_records"
        display_name = "Location Records"
        description = "Raw location pings from Location History."
        pk = ("timestamp", "latitude", "longitude")

    time_at: ClassVar[str] = "timestamp"

    timestamp: Annotated[str, Field(db_type="VARCHAR", description="ISO timestamp", display_name="Timestamp")] = ""
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude", display_name="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude", display_name="Longitude")] = 0.0
    accuracy: Annotated[int, Field(db_type="INTEGER", description="Accuracy in meters", display_name="Accuracy")] = 0
    altitude: Annotated[int, Field(db_type="INTEGER", description="Altitude in meters", display_name="Altitude")] = 0
    source: Annotated[str | None, Field(db_type="VARCHAR", description="Location source", display_name="Location Source")] = (
        None
    )
    device_tag: Annotated[str | None, Field(db_type="VARCHAR", description="Device identifier", display_name="Device Tag")] = (
        None
    )

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "Location History (Timeline)")
        if not files:
            files = iter_files(client, "Location History")
        yield from parse_location_records(files)


class LocationVisits(EventTable):
    """Semantic location visit or activity segment."""

    class _Meta:
        name = "location_visits"
        display_name = "Location Visits"
        description = "Semantic place visits / activity segments."
        pk = ("start_timestamp", "place_name", "type")

    time_at: ClassVar[str] = "start_timestamp"

    start_timestamp: Annotated[str, Field(db_type="VARCHAR", description="Start ISO timestamp", display_name="Start Time")] = (
        ""
    )
    place_name: Annotated[
        str, Field(db_type="VARCHAR", description="Place name or activity type", display_name="Place Name")
    ] = ""
    type: Annotated[str, Field(db_type="VARCHAR", description="Entry type: visit or activity", display_name="Type")] = ""
    place_address: Annotated[str | None, Field(db_type="VARCHAR", description="Place address", display_name="Address")] = None
    place_id: Annotated[str | None, Field(db_type="VARCHAR", description="Google place ID", display_name="Place ID")] = None
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude", display_name="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude", display_name="Longitude")] = 0.0
    end_timestamp: Annotated[
        str | None, Field(db_type="VARCHAR", description="End ISO timestamp", display_name="End Time")
    ] = None
    confidence: Annotated[str | None, Field(db_type="VARCHAR", description="Confidence level", display_name="Confidence")] = (
        None
    )

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "Location History (Timeline)/Semantic Location History")
        if not files:
            files = iter_files(client, "Location History/Semantic Location History")
        yield from parse_semantic_locations(files)


class YouTubeWatchHistory(EventTable):
    """YouTube watch history entry."""

    class _Meta:
        name = "youtube_watch_history"
        display_name = "YouTube Watch History"
        description = "YouTube watch history events."
        pk = ("title_url", "time")

    time_at: ClassVar[str] = "time"

    title_url: Annotated[str, Field(db_type="VARCHAR", description="Video URL", display_name="Video URL")] = ""
    time: Annotated[str, Field(db_type="VARCHAR", description="Watch timestamp", display_name="Watch Time")] = ""
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Video title", display_name="Title")] = None
    channel_name: Annotated[str | None, Field(db_type="VARCHAR", description="Channel name", display_name="Channel Name")] = (
        None
    )
    channel_url: Annotated[str | None, Field(db_type="VARCHAR", description="Channel URL", display_name="Channel URL")] = None
    product: Annotated[
        str | None, Field(db_type="VARCHAR", description="Product (YouTube or YouTube Music)", display_name="Product")
    ] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "YouTube and YouTube Music/history")
        yield from parse_watch_history(files)


class YouTubeSearchHistory(EventTable):
    """YouTube search history entry."""

    class _Meta:
        name = "youtube_search_history"
        display_name = "YouTube Search History"
        description = "YouTube search history events."
        pk = ("title", "time")

    time_at: ClassVar[str] = "time"

    title: Annotated[str, Field(db_type="VARCHAR", description="Search query", display_name="Search Query")] = ""
    time: Annotated[str, Field(db_type="VARCHAR", description="Search timestamp", display_name="Search Time")] = ""
    title_url: Annotated[str | None, Field(db_type="VARCHAR", description="Search URL", display_name="Search URL")] = None
    product: Annotated[str | None, Field(db_type="VARCHAR", description="Product header", display_name="Product")] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "YouTube and YouTube Music/history")
        yield from parse_search_history(files)


class YouTubeSubscriptions(SnapshotTable):
    """YouTube subscriptions. SCD2 closes a row when the user unsubscribes."""

    class _Meta:
        name = "youtube_subscriptions"
        display_name = "YouTube Subscriptions"
        description = "Channels the user is subscribed to."
        pk = ("channel_id",)

    channel_id: Annotated[str, Field(db_type="VARCHAR", description="YouTube channel ID", display_name="Channel ID")] = ""
    channel_url: Annotated[str | None, Field(db_type="VARCHAR", description="Channel URL", display_name="Channel URL")] = None
    channel_title: Annotated[
        str | None, Field(db_type="VARCHAR", description="Channel title", display_name="Channel Title")
    ] = None

    @classmethod
    def extract(cls, client: Path, **_: Any) -> Iterator[dict[str, Any]]:
        files = iter_files(client, "YouTube and YouTube Music/subscriptions", suffix=".csv")
        yield from parse_subscriptions(files)


TABLES: tuple[type[SourceTable], ...] = (
    PhotosMetadata,
    LocationRecords,
    LocationVisits,
    YouTubeWatchHistory,
    YouTubeSearchHistory,
    YouTubeSubscriptions,
)
