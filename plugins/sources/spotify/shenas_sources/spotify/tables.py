"""Spotify raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class RecentlyPlayed:
    """Recently played track."""

    __table__: ClassVar[str] = "recently_played"
    __pk__: ClassVar[tuple[str, ...]] = ("played_at",)
    __kind__: ClassVar[TableKind] = "event"

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
    __kind__: ClassVar[TableKind] = "snapshot"

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
    __kind__: ClassVar[TableKind] = "snapshot"

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
    __kind__: ClassVar[TableKind] = "snapshot"

    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID")]
    added_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When the track was saved")] = None
    track_name: Annotated[str | None, Field(db_type="VARCHAR", description="Track name")] = None
    artists: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated artist names")] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name")] = None
    duration_ms: Annotated[int, Field(db_type="INTEGER", description="Track duration in milliseconds")] = 0
    popularity: Annotated[int, Field(db_type="INTEGER", description="Track popularity (0-100)")] = 0


@dataclass
class AudioFeatures:
    """Spotify audio analysis features for a single track."""

    __table__: ClassVar[str] = "audio_features"
    __pk__: ClassVar[tuple[str, ...]] = ("track_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID")]
    danceability: Annotated[float | None, Field(db_type="DOUBLE", description="Danceability (0..1)")] = None
    energy: Annotated[float | None, Field(db_type="DOUBLE", description="Energy (0..1)")] = None
    key: Annotated[int | None, Field(db_type="INTEGER", description="Pitch class (0..11)")] = None
    loudness: Annotated[float | None, Field(db_type="DOUBLE", description="Loudness (dB)")] = None
    mode: Annotated[int | None, Field(db_type="INTEGER", description="Mode (0=minor, 1=major)")] = None
    speechiness: Annotated[float | None, Field(db_type="DOUBLE", description="Speechiness (0..1)")] = None
    acousticness: Annotated[float | None, Field(db_type="DOUBLE", description="Acousticness (0..1)")] = None
    instrumentalness: Annotated[float | None, Field(db_type="DOUBLE", description="Instrumentalness (0..1)")] = None
    liveness: Annotated[float | None, Field(db_type="DOUBLE", description="Liveness (0..1)")] = None
    valence: Annotated[float | None, Field(db_type="DOUBLE", description="Valence / positivity (0..1)")] = None
    tempo: Annotated[float | None, Field(db_type="DOUBLE", description="Tempo (BPM)")] = None
    time_signature: Annotated[int | None, Field(db_type="INTEGER", description="Time signature")] = None
    duration_ms: Annotated[int | None, Field(db_type="INTEGER", description="Track duration (ms)")] = None


@dataclass
class UserProfile:
    """Authenticated Spotify user profile."""

    __table__: ClassVar[str] = "user_profile"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[str, Field(db_type="VARCHAR", description="Spotify user ID")]
    display_name: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    email: Annotated[str | None, Field(db_type="VARCHAR", description="Email")] = None
    country: Annotated[str | None, Field(db_type="VARCHAR", description="Country code")] = None
    product: Annotated[str | None, Field(db_type="VARCHAR", description="Subscription tier (free / premium)")] = None
    followers: Annotated[int | None, Field(db_type="INTEGER", description="Follower count")] = None
    image_url: Annotated[str | None, Field(db_type="VARCHAR", description="Profile image URL")] = None


@dataclass
class FollowedArtist:
    """An artist the user follows."""

    __table__: ClassVar[str] = "followed_artists"
    __pk__: ClassVar[tuple[str, ...]] = ("artist_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    artist_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify artist ID")]
    artist_name: Annotated[str | None, Field(db_type="VARCHAR", description="Artist name")] = None
    genres: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated genres")] = None
    popularity: Annotated[int, Field(db_type="INTEGER", description="Popularity (0-100)")] = 0
    followers: Annotated[int, Field(db_type="INTEGER", description="Follower count")] = 0


@dataclass
class SavedAlbum:
    """An album in the user's library."""

    __table__: ClassVar[str] = "saved_albums"
    __pk__: ClassVar[tuple[str, ...]] = ("album_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    album_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify album ID")]
    added_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When the album was saved")] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name")] = None
    artists: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated artist names")] = None
    release_date: Annotated[str | None, Field(db_type="VARCHAR", description="Release date")] = None
    total_tracks: Annotated[int, Field(db_type="INTEGER", description="Total tracks")] = 0
    label: Annotated[str | None, Field(db_type="VARCHAR", description="Record label")] = None
    popularity: Annotated[int, Field(db_type="INTEGER", description="Popularity (0-100)")] = 0


@dataclass
class Playlist:
    """A user playlist (metadata only -- not contents)."""

    __table__: ClassVar[str] = "playlists"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[str, Field(db_type="VARCHAR", description="Playlist ID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Playlist name")] = None
    description: Annotated[str | None, Field(db_type="TEXT", description="Description")] = None
    owner_id: Annotated[str | None, Field(db_type="VARCHAR", description="Owner ID")] = None
    owner_name: Annotated[str | None, Field(db_type="VARCHAR", description="Owner display name")] = None
    public: Annotated[bool, Field(db_type="BOOLEAN", description="Public playlist")] = False
    collaborative: Annotated[bool, Field(db_type="BOOLEAN", description="Collaborative playlist")] = False
    track_count: Annotated[int, Field(db_type="INTEGER", description="Number of tracks")] = 0
    snapshot_id: Annotated[str | None, Field(db_type="VARCHAR", description="Spotify snapshot ID")] = None
    image_url: Annotated[str | None, Field(db_type="VARCHAR", description="Cover image URL")] = None


@dataclass
class SavedShow:
    """A podcast show in the user's library."""

    __table__: ClassVar[str] = "saved_shows"
    __pk__: ClassVar[tuple[str, ...]] = ("show_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    show_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify show ID")]
    added_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When the show was saved")] = None
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Show name")] = None
    publisher: Annotated[str | None, Field(db_type="VARCHAR", description="Publisher")] = None
    description: Annotated[str | None, Field(db_type="TEXT", description="Description")] = None
    total_episodes: Annotated[int, Field(db_type="INTEGER", description="Total episodes")] = 0
    languages: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated languages")] = None


@dataclass
class SavedEpisode:
    """A podcast episode the user has saved."""

    __table__: ClassVar[str] = "saved_episodes"
    __pk__: ClassVar[tuple[str, ...]] = ("episode_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    episode_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify episode ID")]
    added_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When saved")] = None
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Episode name")] = None
    show_name: Annotated[str | None, Field(db_type="VARCHAR", description="Show name")] = None
    publisher: Annotated[str | None, Field(db_type="VARCHAR", description="Publisher")] = None
    description: Annotated[str | None, Field(db_type="TEXT", description="Description")] = None
    duration_ms: Annotated[int, Field(db_type="INTEGER", description="Episode duration (ms)")] = 0
    release_date: Annotated[str | None, Field(db_type="VARCHAR", description="Release date")] = None
    languages: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated languages")] = None
