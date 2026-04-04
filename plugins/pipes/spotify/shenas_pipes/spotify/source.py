"""Spotify dlt resources -- recently played, top tracks/artists, saved tracks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dlt

from shenas_pipes.spotify.tables import RecentlyPlayed, SavedTrack, TopArtist, TopTrack
from shenas_schemas.core.dlt import dataclass_to_dlt_columns

if TYPE_CHECKING:
    from collections.abc import Iterator

    import spotipy


def _artists_str(artists: list[dict[str, Any]]) -> str:
    """Join artist names from a track's artists array."""
    return ", ".join(a.get("name", "") for a in artists if a.get("name"))


@dlt.resource(
    write_disposition="merge",
    primary_key=list(RecentlyPlayed.__pk__),
    columns=dataclass_to_dlt_columns(RecentlyPlayed),
)
def recently_played(
    client: spotipy.Spotify,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("played_at", initial_value=None),
) -> Iterator[dict[str, Any]]:
    """Yield recently played tracks (up to 50 per call).

    Uses the 'after' cursor to only fetch tracks since last sync.
    Poll this frequently (~1-2 hours) to build a complete history.
    """
    params: dict[str, Any] = {"limit": 50}
    if cursor.last_value:
        from datetime import datetime

        dt = datetime.fromisoformat(cursor.last_value)
        after_ms = int(dt.timestamp() * 1000)
        params["after"] = after_ms

    result = client.current_user_recently_played(**params)
    for item in result.get("items", []):
        track = item.get("track", {})
        album = track.get("album", {})
        yield {
            "played_at": item.get("played_at", ""),
            "track_id": track.get("id", ""),
            "track_name": track.get("name", ""),
            "artists": _artists_str(track.get("artists", [])),
            "album_name": album.get("name", ""),
            "album_release_date": album.get("release_date", ""),
            "duration_ms": track.get("duration_ms", 0),
            "explicit": track.get("explicit", False),
            "popularity": track.get("popularity", 0),
            "track_uri": track.get("uri", ""),
        }


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(TopTrack))
def top_tracks(client: spotipy.Spotify, time_range: str = "medium_term") -> Iterator[dict[str, Any]]:
    """Yield the user's top tracks for a time range."""
    offset = 0
    while True:
        result = client.current_user_top_tracks(limit=50, offset=offset, time_range=time_range)
        items = result.get("items", [])
        if not items:
            break
        for i, track in enumerate(items):
            album = track.get("album", {})
            yield {
                "rank": offset + i + 1,
                "time_range": time_range,
                "track_id": track.get("id", ""),
                "track_name": track.get("name", ""),
                "artists": _artists_str(track.get("artists", [])),
                "album_name": album.get("name", ""),
                "popularity": track.get("popularity", 0),
                "duration_ms": track.get("duration_ms", 0),
            }
        if len(items) < 50:
            break
        offset += 50


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(TopArtist))
def top_artists(client: spotipy.Spotify, time_range: str = "medium_term") -> Iterator[dict[str, Any]]:
    """Yield the user's top artists for a time range."""
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


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(SavedTrack))
def saved_tracks(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the user's saved/liked tracks."""
    offset = 0
    while True:
        result = client.current_user_saved_tracks(limit=50, offset=offset)
        items = result.get("items", [])
        if not items:
            break
        for item in items:
            track = item.get("track", {})
            album = track.get("album", {})
            yield {
                "added_at": item.get("added_at", ""),
                "track_id": track.get("id", ""),
                "track_name": track.get("name", ""),
                "artists": _artists_str(track.get("artists", [])),
                "album_name": album.get("name", ""),
                "duration_ms": track.get("duration_ms", 0),
                "popularity": track.get("popularity", 0),
            }
        if len(items) < 50:
            break
        offset += 50
