"""Spotify raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_schemas.core.field import Field


@dataclass
class RecentlyPlayed:
    """Recently played track."""

    __table__: ClassVar[str] = "recently_played"
    __pk__: ClassVar[tuple[str, ...]] = ("played_at",)

    played_at: Annotated[str, Field(db_type="TIMESTAMP", description="When the track was played")]
    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID")]
    track_name: Annotated[str | None, Field(db_type="VARCHAR", description="Track name")] = None
    artists: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated artist names")] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name")] = None
    album_release_date: Annotated[str | None, Field(db_type="VARCHAR", description="Album release date")] = None
    duration_ms: Annotated[int, Field(db_type="INTEGER", description="Track duration in milliseconds")] = 0
    explicit: Annotated[bool, Field(db_type="BOOLEAN", description="Whether the track is explicit")] = False
    popularity: Annotated[int, Field(db_type="INTEGER", description="Track popularity (0-100)")] = 0
    track_uri: Annotated[str | None, Field(db_type="VARCHAR", description="Spotify track URI")] = None


@dataclass
class TopTrack:
    """Top track for a time range."""

    __table__: ClassVar[str] = "top_tracks"
    __pk__: ClassVar[tuple[str, ...]] = ("track_id", "time_range")

    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID")]
    time_range: Annotated[str, Field(db_type="VARCHAR", description="Time range (short, medium, long)")]
    rank: Annotated[int, Field(db_type="INTEGER", description="Rank position")] = 0
    track_name: Annotated[str | None, Field(db_type="VARCHAR", description="Track name")] = None
    artists: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated artist names")] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name")] = None
    popularity: Annotated[int, Field(db_type="INTEGER", description="Track popularity (0-100)")] = 0
    duration_ms: Annotated[int, Field(db_type="INTEGER", description="Track duration in milliseconds")] = 0


@dataclass
class TopArtist:
    """Top artist for a time range."""

    __table__: ClassVar[str] = "top_artists"
    __pk__: ClassVar[tuple[str, ...]] = ("artist_id", "time_range")

    artist_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify artist ID")]
    time_range: Annotated[str, Field(db_type="VARCHAR", description="Time range (short, medium, long)")]
    rank: Annotated[int, Field(db_type="INTEGER", description="Rank position")] = 0
    artist_name: Annotated[str | None, Field(db_type="VARCHAR", description="Artist name")] = None
    genres: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated genres")] = None
    popularity: Annotated[int, Field(db_type="INTEGER", description="Artist popularity (0-100)")] = 0
    followers: Annotated[int, Field(db_type="INTEGER", description="Number of followers")] = 0


@dataclass
class SavedTrack:
    """Saved/liked track."""

    __table__: ClassVar[str] = "saved_tracks"
    __pk__: ClassVar[tuple[str, ...]] = ("track_id",)

    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID")]
    added_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When the track was saved")] = None
    track_name: Annotated[str | None, Field(db_type="VARCHAR", description="Track name")] = None
    artists: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated artist names")] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name")] = None
    duration_ms: Annotated[int, Field(db_type="INTEGER", description="Track duration in milliseconds")] = 0
    popularity: Annotated[int, Field(db_type="INTEGER", description="Track popularity (0-100)")] = 0
