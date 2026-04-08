"""Spotify dlt resources -- recently played, top tracks/artists, saved tracks,
audio features, user profile, followed artists, saved albums, playlists,
saved shows, saved episodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.spotify.tables import (
    AudioFeatures,
    FollowedArtist,
    Playlist,
    RecentlyPlayed,
    SavedAlbum,
    SavedEpisode,
    SavedShow,
    SavedTrack,
    TopArtist,
    TopTrack,
    UserProfile,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    import spotipy


# Track ids collected by recently_played / top_tracks / saved_tracks during a
# single sync, drained by audio_features. Cleared at the start of every sync
# inside source.resources().
_TRACK_IDS: set[str] = set()


def _artists_str(artists: list[dict[str, Any]]) -> str:
    """Join artist names from a track's artists array."""
    return ", ".join(a.get("name", "") for a in artists if a.get("name"))


def _record_track_id(track_id: str | None) -> None:
    if track_id:
        _TRACK_IDS.add(track_id)


def reset_track_id_cache() -> None:
    """Called from source.resources() at the start of every sync."""
    _TRACK_IDS.clear()


TIME_RANGES = ("short_term", "medium_term", "long_term")


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


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(TopTrack))
def top_tracks(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the user's top tracks for all three time ranges."""
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


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(TopArtist))
def top_artists(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the user's top artists for all three time ranges."""
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


@dlt.resource(
    name="audio_features",
    write_disposition="merge",
    primary_key=list(AudioFeatures.__pk__),
    columns=dataclass_to_dlt_columns(AudioFeatures),
)
def audio_features(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield Spotify audio features for every track id collected during this sync.

    Drained from the module-level _TRACK_IDS set populated by recently_played,
    top_tracks and saved_tracks. Spotify allows up to 100 ids per batch.
    """
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


@dlt.resource(name="user_profile", write_disposition="replace", columns=dataclass_to_dlt_columns(UserProfile))
def user_profile(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the authenticated Spotify user profile (single row)."""
    me = client.current_user()
    if not me:
        return
    images = me.get("images") or []
    yield {
        "id": me.get("id", ""),
        "display_name": me.get("display_name"),
        "email": me.get("email"),
        "country": me.get("country"),
        "product": me.get("product"),
        "followers": (me.get("followers") or {}).get("total"),
        "image_url": images[0].get("url") if images else None,
    }


@dlt.resource(
    name="followed_artists",
    write_disposition="replace",
    columns=dataclass_to_dlt_columns(FollowedArtist),
)
def followed_artists(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the artists the user follows."""
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


@dlt.resource(name="saved_albums", write_disposition="replace", columns=dataclass_to_dlt_columns(SavedAlbum))
def saved_albums(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the user's saved albums."""
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


@dlt.resource(name="playlists", write_disposition="replace", columns=dataclass_to_dlt_columns(Playlist))
def playlists(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the user's playlists (metadata only)."""
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
                "name": p.get("name"),
                "description": p.get("description"),
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


@dlt.resource(name="saved_shows", write_disposition="replace", columns=dataclass_to_dlt_columns(SavedShow))
def saved_shows(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the user's saved podcast shows."""
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
                "name": show.get("name"),
                "publisher": show.get("publisher"),
                "description": show.get("description"),
                "total_episodes": show.get("total_episodes", 0),
                "languages": ", ".join(show.get("languages") or []),
            }
        if len(items) < 50:
            break
        offset += 50


@dlt.resource(name="saved_episodes", write_disposition="replace", columns=dataclass_to_dlt_columns(SavedEpisode))
def saved_episodes(client: spotipy.Spotify) -> Iterator[dict[str, Any]]:
    """Yield the user's saved podcast episodes."""
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
                "name": episode.get("name"),
                "show_name": show.get("name"),
                "publisher": show.get("publisher"),
                "description": episode.get("description"),
                "duration_ms": episode.get("duration_ms", 0),
                "release_date": episode.get("release_date"),
                "languages": ", ".join(episode.get("languages") or []),
            }
        if len(items) < 50:
            break
        offset += 50
