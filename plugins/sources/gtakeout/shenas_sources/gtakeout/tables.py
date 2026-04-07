"""Google Takeout raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class PhotoMetadata:
    """Google Photos metadata from Takeout."""

    __table__: ClassVar[str] = "photos_metadata"
    __pk__: ClassVar[tuple[str, ...]] = ("title", "photo_taken_timestamp")
    __kind__: ClassVar[TableKind] = "event"

    title: Annotated[str, Field(db_type="VARCHAR", description="Photo/video title")]
    photo_taken_timestamp: Annotated[str, Field(db_type="VARCHAR", description="Epoch timestamp when photo was taken")]
    description: Annotated[str | None, Field(db_type="TEXT", description="Photo description")] = None
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


@dataclass
class LocationRecord:
    """Raw location record from Location History."""

    __table__: ClassVar[str] = "location_records"
    __pk__: ClassVar[tuple[str, ...]] = ("timestamp", "latitude", "longitude")
    __kind__: ClassVar[TableKind] = "event"

    timestamp: Annotated[str, Field(db_type="VARCHAR", description="ISO timestamp")]
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude")] = 0.0
    accuracy: Annotated[int, Field(db_type="INTEGER", description="Accuracy in meters")] = 0
    altitude: Annotated[int, Field(db_type="INTEGER", description="Altitude in meters")] = 0
    source: Annotated[str | None, Field(db_type="VARCHAR", description="Location source")] = None
    device_tag: Annotated[str | None, Field(db_type="VARCHAR", description="Device identifier")] = None


@dataclass
class LocationVisit:
    """Semantic location visit or activity segment."""

    __table__: ClassVar[str] = "location_visits"
    __pk__: ClassVar[tuple[str, ...]] = ("start_timestamp", "place_name", "type")
    __kind__: ClassVar[TableKind] = "event"

    start_timestamp: Annotated[str, Field(db_type="VARCHAR", description="Start ISO timestamp")]
    place_name: Annotated[str, Field(db_type="VARCHAR", description="Place name or activity type")]
    type: Annotated[str, Field(db_type="VARCHAR", description="Entry type: visit or activity")]
    place_address: Annotated[str | None, Field(db_type="VARCHAR", description="Place address")] = None
    place_id: Annotated[str | None, Field(db_type="VARCHAR", description="Google place ID")] = None
    latitude: Annotated[float, Field(db_type="DOUBLE", description="Latitude")] = 0.0
    longitude: Annotated[float, Field(db_type="DOUBLE", description="Longitude")] = 0.0
    end_timestamp: Annotated[str | None, Field(db_type="VARCHAR", description="End ISO timestamp")] = None
    confidence: Annotated[str | None, Field(db_type="VARCHAR", description="Confidence level")] = None


@dataclass
class YouTubeWatchHistory:
    """YouTube watch history entry."""

    __table__: ClassVar[str] = "youtube_watch_history"
    __pk__: ClassVar[tuple[str, ...]] = ("title_url", "time")
    __kind__: ClassVar[TableKind] = "event"

    title_url: Annotated[str, Field(db_type="VARCHAR", description="Video URL")]
    time: Annotated[str, Field(db_type="VARCHAR", description="Watch timestamp")]
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Video title")] = None
    channel_name: Annotated[str | None, Field(db_type="VARCHAR", description="Channel name")] = None
    channel_url: Annotated[str | None, Field(db_type="VARCHAR", description="Channel URL")] = None
    product: Annotated[str | None, Field(db_type="VARCHAR", description="Product (YouTube or YouTube Music)")] = None


@dataclass
class YouTubeSearchHistory:
    """YouTube search history entry."""

    __table__: ClassVar[str] = "youtube_search_history"
    __pk__: ClassVar[tuple[str, ...]] = ("title", "time")
    __kind__: ClassVar[TableKind] = "event"

    title: Annotated[str, Field(db_type="VARCHAR", description="Search query")]
    time: Annotated[str, Field(db_type="VARCHAR", description="Search timestamp")]
    title_url: Annotated[str | None, Field(db_type="VARCHAR", description="Search URL")] = None
    product: Annotated[str | None, Field(db_type="VARCHAR", description="Product header")] = None


@dataclass
class YouTubeSubscription:
    """YouTube subscription."""

    __table__: ClassVar[str] = "youtube_subscriptions"
    __pk__: ClassVar[tuple[str, ...]] = ("channel_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    channel_id: Annotated[str, Field(db_type="VARCHAR", description="YouTube channel ID")]
    channel_url: Annotated[str | None, Field(db_type="VARCHAR", description="Channel URL")] = None
    channel_title: Annotated[str | None, Field(db_type="VARCHAR", description="Channel title")] = None
