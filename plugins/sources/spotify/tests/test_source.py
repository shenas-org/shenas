from __future__ import annotations

from unittest.mock import MagicMock

from shenas_sources.spotify.resources import (
    audio_features,
    followed_artists,
    playlists,
    recently_played,
    reset_track_id_cache,
    saved_albums,
    saved_episodes,
    saved_shows,
    saved_tracks,
    top_artists,
    top_tracks,
    user_profile,
)


class TestRecentlyPlayed:
    def test_yields_tracks(self) -> None:
        reset_track_id_cache()
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
    def test_yields_ranked_tracks_for_all_time_ranges(self) -> None:
        reset_track_id_cache()
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

        results = list(top_tracks(client))
        # 1 row per time range x 3 time ranges
        assert len(results) == 3
        ranges = {r["time_range"] for r in results}
        assert ranges == {"short_term", "medium_term", "long_term"}
        assert all(r["rank"] == 1 for r in results)


class TestTopArtists:
    def test_yields_ranked_artists_for_all_time_ranges(self) -> None:
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
        assert len(results) == 3
        assert all(r["artist_name"] == "Fav Artist" for r in results)
        ranges = {r["time_range"] for r in results}
        assert ranges == {"short_term", "medium_term", "long_term"}


class TestSavedTracks:
    def test_yields_saved(self) -> None:
        reset_track_id_cache()
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


class TestAudioFeatures:
    def test_drains_collected_track_ids(self) -> None:
        reset_track_id_cache()
        client = MagicMock()
        # Populate cache by running recently_played first
        client.current_user_recently_played.return_value = {
            "items": [
                {
                    "played_at": "2026-03-29T14:30:00.000Z",
                    "track": {"id": "t1", "name": "x", "artists": [], "album": {}},
                }
            ]
        }
        list(recently_played(client))

        client.audio_features.return_value = [
            {
                "id": "t1",
                "danceability": 0.8,
                "energy": 0.7,
                "key": 5,
                "loudness": -6.2,
                "mode": 1,
                "speechiness": 0.05,
                "acousticness": 0.1,
                "instrumentalness": 0.0,
                "liveness": 0.2,
                "valence": 0.6,
                "tempo": 120.0,
                "time_signature": 4,
                "duration_ms": 200000,
            }
        ]

        rows = list(audio_features(client))
        assert len(rows) == 1
        assert rows[0]["track_id"] == "t1"
        assert rows[0]["valence"] == 0.6
        assert rows[0]["tempo"] == 120.0

    def test_skips_none_features(self) -> None:
        reset_track_id_cache()
        client = MagicMock()
        client.current_user_recently_played.return_value = {
            "items": [{"played_at": "2026-03-29T14:30:00.000Z", "track": {"id": "x", "name": "x", "artists": [], "album": {}}}]
        }
        list(recently_played(client))
        client.audio_features.return_value = [None]
        assert list(audio_features(client)) == []


class TestUserProfile:
    def test_yields_profile(self) -> None:
        client = MagicMock()
        client.current_user.return_value = {
            "id": "me",
            "display_name": "Me",
            "email": "me@example.com",
            "country": "SE",
            "product": "premium",
            "followers": {"total": 12},
            "images": [{"url": "https://example.com/me.jpg"}],
        }
        rows = list(user_profile(client))
        assert len(rows) == 1
        assert rows[0]["product"] == "premium"
        assert rows[0]["image_url"] == "https://example.com/me.jpg"


class TestFollowedArtists:
    def test_paginates_via_after(self) -> None:
        client = MagicMock()
        client.current_user_followed_artists.side_effect = [
            {
                "artists": {
                    "items": [{"id": "a1", "name": "A1", "genres": ["rock"], "popularity": 50, "followers": {"total": 1}}],
                    "cursors": {"after": "tok"},
                }
            },
            {"artists": {"items": [], "cursors": {}}},
        ]
        rows = list(followed_artists(client))
        assert len(rows) == 1
        assert rows[0]["artist_id"] == "a1"


class TestSavedAlbums:
    def test_yields_albums(self) -> None:
        client = MagicMock()
        client.current_user_saved_albums.return_value = {
            "items": [
                {
                    "added_at": "2026-01-01T00:00:00Z",
                    "album": {
                        "id": "alb1",
                        "name": "An Album",
                        "artists": [{"name": "Some Artist"}],
                        "release_date": "2024-05-01",
                        "total_tracks": 12,
                        "label": "Some Label",
                        "popularity": 70,
                    },
                }
            ]
        }
        rows = list(saved_albums(client))
        assert len(rows) == 1
        assert rows[0]["album_id"] == "alb1"
        assert rows[0]["artists"] == "Some Artist"


class TestPlaylists:
    def test_yields_playlists(self) -> None:
        client = MagicMock()
        client.current_user_playlists.return_value = {
            "items": [
                {
                    "id": "pl1",
                    "name": "Vibes",
                    "description": "good times",
                    "owner": {"id": "me", "display_name": "Me"},
                    "public": True,
                    "collaborative": False,
                    "tracks": {"total": 42},
                    "snapshot_id": "snap-1",
                    "images": [{"url": "https://example.com/cover.jpg"}],
                }
            ]
        }
        rows = list(playlists(client))
        assert len(rows) == 1
        assert rows[0]["track_count"] == 42
        assert rows[0]["image_url"] == "https://example.com/cover.jpg"


class TestSavedShowsAndEpisodes:
    def test_saved_shows(self) -> None:
        client = MagicMock()
        client.current_user_saved_shows.return_value = {
            "items": [
                {
                    "added_at": "2026-02-01T00:00:00Z",
                    "show": {
                        "id": "s1",
                        "name": "A Show",
                        "publisher": "A Publisher",
                        "description": "About things",
                        "total_episodes": 100,
                        "languages": ["en"],
                    },
                }
            ]
        }
        rows = list(saved_shows(client))
        assert len(rows) == 1
        assert rows[0]["name"] == "A Show"

    def test_saved_episodes(self) -> None:
        client = MagicMock()
        client.current_user_saved_episodes.return_value = {
            "items": [
                {
                    "added_at": "2026-02-01T00:00:00Z",
                    "episode": {
                        "id": "e1",
                        "name": "Episode One",
                        "show": {"name": "A Show", "publisher": "A Publisher"},
                        "description": "topics",
                        "duration_ms": 3600000,
                        "release_date": "2026-01-15",
                        "languages": ["en"],
                    },
                }
            ]
        }
        rows = list(saved_episodes(client))
        assert len(rows) == 1
        assert rows[0]["show_name"] == "A Show"

    def test_saved_shows_handles_failure(self) -> None:
        client = MagicMock()
        client.current_user_saved_shows.side_effect = RuntimeError("podcasts disabled")
        assert list(saved_shows(client)) == []
