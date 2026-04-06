from __future__ import annotations

from unittest.mock import MagicMock

from shenas_sources.spotify.source import recently_played, saved_tracks, top_artists, top_tracks


class TestRecentlyPlayed:
    def test_yields_tracks(self) -> None:
        client = MagicMock()
        client.current_user_recently_played.return_value = {
            "items": [
                {
                    "played_at": "2026-03-29T14:30:00.000Z",
                    "track": {
                        "id": "abc123",
                        "name": "Test Song",
                        "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
                        "album": {"name": "Test Album", "release_date": "2025-01-01"},
                        "duration_ms": 210000,
                        "explicit": False,
                        "popularity": 75,
                        "uri": "spotify:track:abc123",
                    },
                },
            ],
        }

        results = list(recently_played(client))
        assert len(results) == 1
        assert results[0]["track_name"] == "Test Song"
        assert results[0]["artists"] == "Artist A, Artist B"
        assert results[0]["duration_ms"] == 210000

    def test_empty_result(self) -> None:
        client = MagicMock()
        client.current_user_recently_played.return_value = {"items": []}

        results = list(recently_played(client))
        assert len(results) == 0


class TestTopTracks:
    def test_yields_ranked_tracks(self) -> None:
        client = MagicMock()
        client.current_user_top_tracks.return_value = {
            "items": [
                {
                    "id": "t1",
                    "name": "Top Song",
                    "artists": [{"name": "Top Artist"}],
                    "album": {"name": "Top Album"},
                    "popularity": 90,
                    "duration_ms": 200000,
                },
            ],
        }

        results = list(top_tracks(client, time_range="short_term"))
        assert len(results) == 1
        assert results[0]["rank"] == 1
        assert results[0]["time_range"] == "short_term"
        assert results[0]["track_name"] == "Top Song"


class TestTopArtists:
    def test_yields_ranked_artists(self) -> None:
        client = MagicMock()
        client.current_user_top_artists.return_value = {
            "items": [
                {
                    "id": "a1",
                    "name": "Fav Artist",
                    "genres": ["rock", "indie"],
                    "popularity": 85,
                    "followers": {"total": 1000000},
                },
            ],
        }

        results = list(top_artists(client))
        assert len(results) == 1
        assert results[0]["artist_name"] == "Fav Artist"
        assert results[0]["genres"] == "rock, indie"
        assert results[0]["followers"] == 1000000


class TestSavedTracks:
    def test_yields_saved(self) -> None:
        client = MagicMock()
        client.current_user_saved_tracks.return_value = {
            "items": [
                {
                    "added_at": "2025-06-15T10:00:00Z",
                    "track": {
                        "id": "s1",
                        "name": "Saved Song",
                        "artists": [{"name": "Saved Artist"}],
                        "album": {"name": "Saved Album"},
                        "duration_ms": 180000,
                        "popularity": 60,
                    },
                },
            ],
        }

        results = list(saved_tracks(client))
        assert len(results) == 1
        assert results[0]["track_name"] == "Saved Song"
        assert results[0]["added_at"] == "2025-06-15T10:00:00Z"
