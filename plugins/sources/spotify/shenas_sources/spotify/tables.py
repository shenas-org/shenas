"""Spotify source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. The class declares its schema fields, its
metadata, and the extraction logic in one place. Notable design choices:

- ``RecentlyPlayed`` is the only true ``EventTable`` -- a play is a
  point-in-time immutable event with a native timestamp.
- All ``saved_*`` and ``followed_artists`` are ``SnapshotTable`` (loaded as
  SCD2). When the user unsaves an album, untracks an episode, or unfollows
  an artist, dlt's SCD2 closes the row's ``_dlt_valid_to`` instead of
  leaving it alive forever (which is the bug the previous classification
  silently introduced).
- ``TopTrack`` / ``TopArtist`` are also SCD2 snapshots: when a track drops
  out of the top-N for a given time range between syncs, its valid_to is
  closed and the historical "what were my top tracks on date X" query
  works correctly.
- ``AudioFeatures`` drains the per-sync ``_TRACK_IDS`` set populated by
  the other track-yielding tables, so we batch-fetch features in groups
  of 100 without re-walking any of the upstream tables.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.relation import PlotHint
from app.table import Field
from shenas_sources.core.table import (
    EventTable,
    SnapshotTable,
    SourceTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    import spotipy


# ---------------------------------------------------------------------------
# Per-sync track-id set, drained by AudioFeatures
# ---------------------------------------------------------------------------


_TRACK_IDS: set[str] = set()


def reset_track_id_cache() -> None:
    """Called from source.resources() at the start of every sync."""
    _TRACK_IDS.clear()


def _record_track_id(track_id: str | None) -> None:
    if track_id:
        _TRACK_IDS.add(track_id)


def _artists_str(artists: list[dict[str, Any]]) -> str:
    return ", ".join(a.get("name", "") for a in artists if a.get("name"))


TIME_RANGES = ("short_term", "medium_term", "long_term")


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class RecentlyPlayed(EventTable):
    """A single track play."""

    class _Meta:
        name = "recently_played"
        display_name = "Recently Played"
        description = "Track plays from the Spotify recent-listens feed."
        pk = ("played_at",)
        time_at = "played_at"
        plot = (PlotHint("popularity"), PlotHint("duration_ms"))

    cursor_column: ClassVar[str] = "played_at"

    played_at: Annotated[str, Field(db_type="TIMESTAMP", description="When the track was played", display_name="Played At")]
    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID", display_name="Track ID")] = ""
    track_name: Annotated[str | None, Field(db_type="VARCHAR", description="Track name", display_name="Track Name")] = None
    artists: Annotated[
        str | None, Field(db_type="VARCHAR", description="Comma-separated artist names", display_name="Artists")
    ] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name", display_name="Album")] = None
    album_release_date: Annotated[
        str | None, Field(db_type="VARCHAR", description="Album release date", display_name="Release Date")
    ] = None
    duration_ms: Annotated[
        int, Field(db_type="INTEGER", description="Track duration in milliseconds", display_name="Duration", unit="ms")
    ] = 0
    explicit: Annotated[
        bool, Field(db_type="BOOLEAN", description="Whether the track is explicit", display_name="Explicit")
    ] = False
    popularity: Annotated[int, Field(db_type="INTEGER", description="Track popularity (0-100)", display_name="Popularity")] = 0
    track_uri: Annotated[str | None, Field(db_type="VARCHAR", description="Spotify track URI", display_name="Track URI")] = (
        None
    )

    @classmethod
    def extract(cls, client: spotipy.Spotify, *, cursor: Any = None, **_: Any) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"limit": 50}
        if cursor is not None and getattr(cursor, "last_value", None):
            dt = datetime.fromisoformat(cursor.last_value)
            params["after"] = int(dt.timestamp() * 1000)

        result = client.current_user_recently_played(**params)
        for item in result.get("items", []):
            track = item.get("track", {})
            album = track.get("album", {})
            track_id = track.get("id", "")
            _record_track_id(track_id)
            yield {
                "played_at": item.get("played_at", ""),
                "track_id": track_id,
                "track_name": track.get("name", ""),
                "artists": _artists_str(track.get("artists", [])),
                "album_name": album.get("name", ""),
                "album_release_date": album.get("release_date", ""),
                "duration_ms": track.get("duration_ms", 0),
                "explicit": track.get("explicit", False),
                "popularity": track.get("popularity", 0),
                "track_uri": track.get("uri", ""),
            }


# ---------------------------------------------------------------------------
# Snapshots (loaded as SCD2 -- removals close _dlt_valid_to)
# ---------------------------------------------------------------------------


class TopTracks(SnapshotTable):
    """Top tracks per time range. SCD2 closes a row when a track drops out."""

    class _Meta:
        name = "top_tracks"
        display_name = "Top Tracks"
        description = "Top tracks for short / medium / long-term ranges."
        pk = ("track_id", "time_range")

    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID", display_name="Track ID")]
    time_range: Annotated[
        str, Field(db_type="VARCHAR", description="short_term / medium_term / long_term", display_name="Time Range")
    ]
    rank: Annotated[int, Field(db_type="INTEGER", description="Rank position", display_name="Rank")] = 0
    track_name: Annotated[str | None, Field(db_type="VARCHAR", description="Track name", display_name="Track Name")] = None
    artists: Annotated[
        str | None, Field(db_type="VARCHAR", description="Comma-separated artist names", display_name="Artists")
    ] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name", display_name="Album")] = None
    popularity: Annotated[int, Field(db_type="INTEGER", description="Track popularity (0-100)", display_name="Popularity")] = 0
    duration_ms: Annotated[
        int, Field(db_type="INTEGER", description="Track duration in milliseconds", display_name="Duration", unit="ms")
    ] = 0

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        for time_range in TIME_RANGES:
            offset = 0
            while True:
                result = client.current_user_top_tracks(limit=50, offset=offset, time_range=time_range)
                items = result.get("items", [])
                if not items:
                    break
                for i, track in enumerate(items):
                    album = track.get("album", {})
                    track_id = track.get("id", "")
                    _record_track_id(track_id)
                    yield {
                        "rank": offset + i + 1,
                        "time_range": time_range,
                        "track_id": track_id,
                        "track_name": track.get("name", ""),
                        "artists": _artists_str(track.get("artists", [])),
                        "album_name": album.get("name", ""),
                        "popularity": track.get("popularity", 0),
                        "duration_ms": track.get("duration_ms", 0),
                    }
                if len(items) < 50:
                    break
                offset += 50


class TopArtists(SnapshotTable):
    """Top artists per time range. SCD2 closes a row when an artist drops out."""

    class _Meta:
        name = "top_artists"
        display_name = "Top Artists"
        description = "Top artists for short / medium / long-term ranges."
        pk = ("artist_id", "time_range")

    artist_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify artist ID", display_name="Artist ID")]
    time_range: Annotated[
        str, Field(db_type="VARCHAR", description="short_term / medium_term / long_term", display_name="Time Range")
    ]
    rank: Annotated[int, Field(db_type="INTEGER", description="Rank position", display_name="Rank")] = 0
    artist_name: Annotated[str | None, Field(db_type="VARCHAR", description="Artist name", display_name="Artist Name")] = None
    genres: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated genres", display_name="Genres")] = None
    popularity: Annotated[
        int, Field(db_type="INTEGER", description="Artist popularity (0-100)", display_name="Popularity")
    ] = 0
    followers: Annotated[int, Field(db_type="INTEGER", description="Number of followers", display_name="Followers")] = 0

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        for time_range in TIME_RANGES:
            offset = 0
            while True:
                result = client.current_user_top_artists(limit=50, offset=offset, time_range=time_range)
                items = result.get("items", [])
                if not items:
                    break
                for i, artist in enumerate(items):
                    yield {
                        "rank": offset + i + 1,
                        "time_range": time_range,
                        "artist_id": artist.get("id", ""),
                        "artist_name": artist.get("name", ""),
                        "genres": ", ".join(artist.get("genres", [])),
                        "popularity": artist.get("popularity", 0),
                        "followers": artist.get("followers", {}).get("total", 0),
                    }
                if len(items) < 50:
                    break
                offset += 50


class SavedTracks(SnapshotTable):
    """Tracks the user has saved (liked). SCD2 closes a row when unsaved."""

    class _Meta:
        name = "saved_tracks"
        display_name = "Saved Tracks"
        description = "Liked songs in the user's library."
        pk = ("track_id",)

    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID", display_name="Track ID")]
    added_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="When the track was saved", display_name="Added At")
    ] = None
    track_name: Annotated[str | None, Field(db_type="VARCHAR", description="Track name", display_name="Track Name")] = None
    artists: Annotated[
        str | None, Field(db_type="VARCHAR", description="Comma-separated artist names", display_name="Artists")
    ] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name", display_name="Album")] = None
    duration_ms: Annotated[
        int, Field(db_type="INTEGER", description="Track duration in milliseconds", display_name="Duration", unit="ms")
    ] = 0
    popularity: Annotated[int, Field(db_type="INTEGER", description="Track popularity (0-100)", display_name="Popularity")] = 0

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        offset = 0
        while True:
            result = client.current_user_saved_tracks(limit=50, offset=offset)
            items = result.get("items", [])
            if not items:
                break
            for item in items:
                track = item.get("track", {})
                album = track.get("album", {})
                track_id = track.get("id", "")
                _record_track_id(track_id)
                yield {
                    "added_at": item.get("added_at", ""),
                    "track_id": track_id,
                    "track_name": track.get("name", ""),
                    "artists": _artists_str(track.get("artists", [])),
                    "album_name": album.get("name", ""),
                    "duration_ms": track.get("duration_ms", 0),
                    "popularity": track.get("popularity", 0),
                }
            if len(items) < 50:
                break
            offset += 50


class AudioFeatures(SnapshotTable):
    """Spotify audio analysis features per track.

    Drained from the module-level _TRACK_IDS set populated by RecentlyPlayed
    / TopTracks / SavedTracks during the same sync, then fetched in batches
    of 100 ids.
    """

    class _Meta:
        name = "audio_features"
        display_name = "Audio Features"
        description = "Per-track danceability / energy / valence / tempo / etc."
        pk = ("track_id",)

    track_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify track ID", display_name="Track ID")]
    danceability: Annotated[
        float | None, Field(db_type="DOUBLE", description="Danceability (0..1)", display_name="Danceability")
    ] = None
    energy: Annotated[float | None, Field(db_type="DOUBLE", description="Energy (0..1)", display_name="Energy")] = None
    key: Annotated[int | None, Field(db_type="INTEGER", description="Pitch class (0..11)", display_name="Key")] = None
    loudness: Annotated[float | None, Field(db_type="DOUBLE", description="Loudness (dB)", display_name="Loudness")] = None
    mode: Annotated[int | None, Field(db_type="INTEGER", description="Mode (0=minor, 1=major)", display_name="Mode")] = None
    speechiness: Annotated[
        float | None, Field(db_type="DOUBLE", description="Speechiness (0..1)", display_name="Speechiness")
    ] = None
    acousticness: Annotated[
        float | None, Field(db_type="DOUBLE", description="Acousticness (0..1)", display_name="Acousticness")
    ] = None
    instrumentalness: Annotated[
        float | None, Field(db_type="DOUBLE", description="Instrumentalness (0..1)", display_name="Instrumentalness")
    ] = None
    liveness: Annotated[float | None, Field(db_type="DOUBLE", description="Liveness (0..1)", display_name="Liveness")] = None
    valence: Annotated[
        float | None, Field(db_type="DOUBLE", description="Valence / positivity (0..1)", display_name="Valence")
    ] = None
    tempo: Annotated[float | None, Field(db_type="DOUBLE", description="Tempo (BPM)", display_name="Tempo")] = None
    time_signature: Annotated[
        int | None, Field(db_type="INTEGER", description="Time signature", display_name="Time Signature")
    ] = None
    duration_ms: Annotated[
        int | None, Field(db_type="INTEGER", description="Track duration (ms)", display_name="Duration", unit="ms")
    ] = None

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        ids = list(_TRACK_IDS)
        for i in range(0, len(ids), 100):
            batch = ids[i : i + 100]
            try:
                result = client.audio_features(batch) or []
            except Exception:
                continue
            for feat in result:
                if not feat:
                    continue
                yield {
                    "track_id": feat.get("id", ""),
                    "danceability": feat.get("danceability"),
                    "energy": feat.get("energy"),
                    "key": feat.get("key"),
                    "loudness": feat.get("loudness"),
                    "mode": feat.get("mode"),
                    "speechiness": feat.get("speechiness"),
                    "acousticness": feat.get("acousticness"),
                    "instrumentalness": feat.get("instrumentalness"),
                    "liveness": feat.get("liveness"),
                    "valence": feat.get("valence"),
                    "tempo": feat.get("tempo"),
                    "time_signature": feat.get("time_signature"),
                    "duration_ms": feat.get("duration_ms"),
                }


class UserProfile(SnapshotTable):
    """The authenticated Spotify user profile."""

    class _Meta:
        name = "user_profile"
        display_name = "User Profile"
        description = "Authenticated Spotify user profile."
        pk = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Spotify user ID", display_name="User ID")]
    display_name_: Annotated[str | None, Field(db_type="VARCHAR", description="Display name", display_name="Display Name")] = (
        None
    )
    email: Annotated[str | None, Field(db_type="VARCHAR", description="Email", display_name="Email")] = None
    country: Annotated[str | None, Field(db_type="VARCHAR", description="Country code", display_name="Country")] = None
    product: Annotated[
        str | None, Field(db_type="VARCHAR", description="Subscription tier (free / premium)", display_name="Subscription")
    ] = None
    followers: Annotated[int | None, Field(db_type="INTEGER", description="Follower count", display_name="Followers")] = None
    image_url: Annotated[str | None, Field(db_type="VARCHAR", description="Profile image URL", display_name="Image URL")] = (
        None
    )

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        me = client.current_user()
        if not me:
            return
        images = me.get("images") or []
        yield {
            "id": me.get("id", ""),
            "display_name_": me.get("display_name"),
            "email": me.get("email"),
            "country": me.get("country"),
            "product": me.get("product"),
            "followers": (me.get("followers") or {}).get("total"),
            "image_url": images[0].get("url") if images else None,
        }


class FollowedArtists(SnapshotTable):
    """Artists the user follows. SCD2 closes a row when the user unfollows."""

    class _Meta:
        name = "followed_artists"
        display_name = "Followed Artists"
        description = "Artists the user is currently following."
        pk = ("artist_id",)

    artist_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify artist ID", display_name="Artist ID")]
    artist_name: Annotated[str | None, Field(db_type="VARCHAR", description="Artist name", display_name="Artist Name")] = None
    genres: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated genres", display_name="Genres")] = None
    popularity: Annotated[int, Field(db_type="INTEGER", description="Popularity (0-100)", display_name="Popularity")] = 0
    followers: Annotated[int, Field(db_type="INTEGER", description="Follower count", display_name="Followers")] = 0

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        after: str | None = None
        while True:
            result = client.current_user_followed_artists(limit=50, after=after) or {}
            body = result.get("artists") or {}
            items = body.get("items") or []
            if not items:
                break
            for artist in items:
                yield {
                    "artist_id": artist.get("id", ""),
                    "artist_name": artist.get("name"),
                    "genres": ", ".join(artist.get("genres") or []),
                    "popularity": artist.get("popularity", 0),
                    "followers": (artist.get("followers") or {}).get("total", 0),
                }
            cursors = body.get("cursors") or {}
            after = cursors.get("after")
            if not after:
                break


class SavedAlbums(SnapshotTable):
    """Albums saved to the user's library. SCD2 closes a row when removed."""

    class _Meta:
        name = "saved_albums"
        display_name = "Saved Albums"
        description = "Albums in the user's library."
        pk = ("album_id",)

    album_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify album ID", display_name="Album ID")]
    added_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="When the album was saved", display_name="Added At")
    ] = None
    album_name: Annotated[str | None, Field(db_type="VARCHAR", description="Album name", display_name="Album Name")] = None
    artists: Annotated[
        str | None, Field(db_type="VARCHAR", description="Comma-separated artist names", display_name="Artists")
    ] = None
    release_date: Annotated[str | None, Field(db_type="VARCHAR", description="Release date", display_name="Release Date")] = (
        None
    )
    total_tracks: Annotated[int, Field(db_type="INTEGER", description="Total tracks", display_name="Total Tracks")] = 0
    label: Annotated[str | None, Field(db_type="VARCHAR", description="Record label", display_name="Label")] = None
    popularity: Annotated[int, Field(db_type="INTEGER", description="Popularity (0-100)", display_name="Popularity")] = 0

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        offset = 0
        while True:
            result = client.current_user_saved_albums(limit=50, offset=offset)
            items = result.get("items", [])
            if not items:
                break
            for item in items:
                album = item.get("album", {})
                yield {
                    "album_id": album.get("id", ""),
                    "added_at": item.get("added_at"),
                    "album_name": album.get("name"),
                    "artists": _artists_str(album.get("artists", [])),
                    "release_date": album.get("release_date"),
                    "total_tracks": album.get("total_tracks", 0),
                    "label": album.get("label"),
                    "popularity": album.get("popularity", 0),
                }
            if len(items) < 50:
                break
            offset += 50


class Playlists(SnapshotTable):
    """The user's playlists (metadata only). SCD2 closes a row when deleted."""

    class _Meta:
        name = "playlists"
        display_name = "Playlists"
        description = "User playlists -- metadata only, not contents."
        pk = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Playlist ID", display_name="Playlist ID")]
    playlist_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Playlist name", display_name="Playlist Name")
    ] = None
    playlist_description: Annotated[
        str | None, Field(db_type="TEXT", description="Description", display_name="Description")
    ] = None
    owner_id: Annotated[str | None, Field(db_type="VARCHAR", description="Owner ID", display_name="Owner ID")] = None
    owner_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Owner display name", display_name="Owner Name")
    ] = None
    public: Annotated[bool, Field(db_type="BOOLEAN", description="Public playlist", display_name="Public")] = False
    collaborative: Annotated[
        bool, Field(db_type="BOOLEAN", description="Collaborative playlist", display_name="Collaborative")
    ] = False
    track_count: Annotated[int, Field(db_type="INTEGER", description="Number of tracks", display_name="Track Count")] = 0
    snapshot_id: Annotated[
        str | None, Field(db_type="VARCHAR", description="Spotify snapshot ID", display_name="Snapshot ID")
    ] = None
    image_url: Annotated[
        str | None, Field(db_type="VARCHAR", description="Cover image URL", display_name="Cover Image URL")
    ] = None

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        offset = 0
        while True:
            result = client.current_user_playlists(limit=50, offset=offset)
            items = result.get("items", [])
            if not items:
                break
            for p in items:
                owner = p.get("owner") or {}
                images = p.get("images") or []
                yield {
                    "id": p.get("id", ""),
                    "playlist_name": p.get("name"),
                    "playlist_description": p.get("description"),
                    "owner_id": owner.get("id"),
                    "owner_name": owner.get("display_name"),
                    "public": bool(p.get("public", False)),
                    "collaborative": bool(p.get("collaborative", False)),
                    "track_count": (p.get("tracks") or {}).get("total", 0),
                    "snapshot_id": p.get("snapshot_id"),
                    "image_url": images[0].get("url") if images else None,
                }
            if len(items) < 50:
                break
            offset += 50


class SavedShows(SnapshotTable):
    """Podcast shows in the user's library. SCD2 closes a row when removed."""

    class _Meta:
        name = "saved_shows"
        display_name = "Saved Shows"
        description = "Podcast shows in the user's library."
        pk = ("show_id",)

    show_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify show ID", display_name="Show ID")]
    added_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="When the show was saved", display_name="Added At")
    ] = None
    show_name: Annotated[str | None, Field(db_type="VARCHAR", description="Show name", display_name="Show Name")] = None
    publisher: Annotated[str | None, Field(db_type="VARCHAR", description="Publisher", display_name="Publisher")] = None
    show_description: Annotated[str | None, Field(db_type="TEXT", description="Description", display_name="Description")] = (
        None
    )
    total_episodes: Annotated[int, Field(db_type="INTEGER", description="Total episodes", display_name="Total Episodes")] = 0
    languages: Annotated[
        str | None, Field(db_type="VARCHAR", description="Comma-separated languages", display_name="Languages")
    ] = None

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        offset = 0
        while True:
            try:
                result = client.current_user_saved_shows(limit=50, offset=offset)
            except Exception:
                return
            items = result.get("items", [])
            if not items:
                break
            for item in items:
                show = item.get("show", {})
                yield {
                    "show_id": show.get("id", ""),
                    "added_at": item.get("added_at"),
                    "show_name": show.get("name"),
                    "publisher": show.get("publisher"),
                    "show_description": show.get("description"),
                    "total_episodes": show.get("total_episodes", 0),
                    "languages": ", ".join(show.get("languages") or []),
                }
            if len(items) < 50:
                break
            offset += 50


class SavedEpisodes(SnapshotTable):
    """Saved podcast episodes. SCD2 closes a row when removed."""

    class _Meta:
        name = "saved_episodes"
        display_name = "Saved Episodes"
        description = "Saved podcast episodes."
        pk = ("episode_id",)

    episode_id: Annotated[str, Field(db_type="VARCHAR", description="Spotify episode ID", display_name="Episode ID")]
    added_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When saved", display_name="Added At")] = None
    episode_name: Annotated[str | None, Field(db_type="VARCHAR", description="Episode name", display_name="Episode Name")] = (
        None
    )
    show_name: Annotated[str | None, Field(db_type="VARCHAR", description="Show name", display_name="Show Name")] = None
    publisher: Annotated[str | None, Field(db_type="VARCHAR", description="Publisher", display_name="Publisher")] = None
    episode_description: Annotated[
        str | None, Field(db_type="TEXT", description="Description", display_name="Description")
    ] = None
    duration_ms: Annotated[
        int, Field(db_type="INTEGER", description="Episode duration (ms)", display_name="Duration", unit="ms")
    ] = 0
    release_date: Annotated[str | None, Field(db_type="VARCHAR", description="Release date", display_name="Release Date")] = (
        None
    )
    languages: Annotated[
        str | None, Field(db_type="VARCHAR", description="Comma-separated languages", display_name="Languages")
    ] = None

    @classmethod
    def extract(cls, client: spotipy.Spotify, **_: Any) -> Iterator[dict[str, Any]]:
        offset = 0
        while True:
            try:
                result = client.current_user_saved_episodes(limit=50, offset=offset)
            except Exception:
                return
            items = result.get("items", [])
            if not items:
                break
            for item in items:
                episode = item.get("episode", {})
                show = episode.get("show", {}) or {}
                yield {
                    "episode_id": episode.get("id", ""),
                    "added_at": item.get("added_at"),
                    "episode_name": episode.get("name"),
                    "show_name": show.get("name"),
                    "publisher": show.get("publisher"),
                    "episode_description": episode.get("description"),
                    "duration_ms": episode.get("duration_ms", 0),
                    "release_date": episode.get("release_date"),
                    "languages": ", ".join(episode.get("languages") or []),
                }
            if len(items) < 50:
                break
            offset += 50


# Order matters: track-yielding tables run BEFORE AudioFeatures so the
# _TRACK_IDS cache is populated by the time AudioFeatures iterates.
TABLES: tuple[type[SourceTable], ...] = (
    RecentlyPlayed,
    TopTracks,
    TopArtists,
    SavedTracks,
    AudioFeatures,
    UserProfile,
    FollowedArtists,
    SavedAlbums,
    Playlists,
    SavedShows,
    SavedEpisodes,
)
