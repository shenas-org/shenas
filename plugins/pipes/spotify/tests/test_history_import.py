from __future__ import annotations

import json
from typing import TYPE_CHECKING

from shenas_pipes.spotify.history_import import streaming_history

if TYPE_CHECKING:
    from pathlib import Path


class TestExtendedFormat:
    def test_parses_endsong(self, tmp_path: Path) -> None:
        data = [
            {
                "ts": "2026-03-28T14:30:00Z",
                "master_metadata_track_name": "Test Song",
                "master_metadata_album_artist_name": "Test Artist",
                "master_metadata_album_album_name": "Test Album",
                "ms_played": 210000,
                "spotify_track_uri": "spotify:track:abc123",
                "reason_start": "clickrow",
                "reason_end": "trackdone",
                "shuffle": False,
                "skipped": False,
                "offline": False,
                "platform": "Linux",
            },
        ]
        (tmp_path / "endsong_0.json").write_text(json.dumps(data))

        results = list(streaming_history(tmp_path))
        assert len(results) == 1
        assert results[0]["track_name"] == "Test Song"
        assert results[0]["artist_name"] == "Test Artist"
        assert results[0]["ms_played"] == 210000
        assert results[0]["spotify_track_uri"] == "spotify:track:abc123"
        assert results[0]["skipped"] is False

    def test_skips_podcast_entries(self, tmp_path: Path) -> None:
        data = [
            {
                "ts": "2026-03-28T14:30:00Z",
                "master_metadata_track_name": None,
                "episode_name": "Some Podcast Episode",
                "ms_played": 300000,
            },
        ]
        (tmp_path / "endsong_0.json").write_text(json.dumps(data))

        results = list(streaming_history(tmp_path))
        assert len(results) == 0


class TestCurrentBasicFormat:
    def test_parses_streaming_history_audio(self, tmp_path: Path) -> None:
        data = [
            {
                "ts": "2026-03-28T14:30:00Z",
                "master_metadata_track_name": "Basic Song",
                "master_metadata_album_artist_name": "Basic Artist",
                "master_metadata_album_album_name": "Basic Album",
                "ms_played": 180000,
            },
        ]
        (tmp_path / "Streaming_History_Audio_0.json").write_text(json.dumps(data))

        results = list(streaming_history(tmp_path))
        assert len(results) == 1
        assert results[0]["track_name"] == "Basic Song"
        assert results[0]["spotify_track_uri"] is None


class TestLegacyFormat:
    def test_parses_legacy(self, tmp_path: Path) -> None:
        data = [
            {
                "endTime": "2025-07-23 14:30",
                "artistName": "Legacy Artist",
                "trackName": "Legacy Song",
                "msPlayed": 150000,
            },
        ]
        (tmp_path / "StreamingHistory0.json").write_text(json.dumps(data))

        results = list(streaming_history(tmp_path))
        assert len(results) == 1
        assert results[0]["track_name"] == "Legacy Song"
        assert results[0]["artist_name"] == "Legacy Artist"
        assert results[0]["played_at"] == "2025-07-23T14:30:00Z"
        assert results[0]["album_name"] == ""


class TestMultipleFiles:
    def test_reads_all_files(self, tmp_path: Path) -> None:
        for i in range(3):
            data = [
                {
                    "ts": f"2026-03-{28 + i}T10:00:00Z",
                    "master_metadata_track_name": f"Song {i}",
                    "master_metadata_album_artist_name": "Artist",
                    "master_metadata_album_album_name": "Album",
                    "ms_played": 200000,
                }
            ]
            (tmp_path / f"endsong_{i}.json").write_text(json.dumps(data))

        results = list(streaming_history(tmp_path))
        assert len(results) == 3

    def test_empty_directory(self, tmp_path: Path) -> None:
        results = list(streaming_history(tmp_path))
        assert len(results) == 0
