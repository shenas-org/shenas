"""Tests for Google Takeout parsers."""

import json
from pathlib import Path

import pytest

from shenas_pipes.gtakeout.parsers.location import parse_location_records, parse_semantic_locations
from shenas_pipes.gtakeout.parsers.photos import parse_photos_metadata
from shenas_pipes.gtakeout.parsers.youtube import parse_search_history, parse_subscriptions, parse_watch_history


@pytest.fixture()
def tmp(tmp_path: Path) -> Path:
    return tmp_path


class TestPhotosParser:
    def test_parses_photo_metadata(self, tmp: Path) -> None:
        f = tmp / "IMG_001.jpg.json"
        f.write_text(
            json.dumps(
                {
                    "title": "IMG_001.jpg",
                    "description": "A sunset",
                    "photoTakenTime": {"timestamp": "1711641600", "formatted": "Mar 28, 2024"},
                    "creationTime": {"timestamp": "1711641600", "formatted": "Mar 28, 2024"},
                    "geoData": {"latitude": 59.33, "longitude": 18.07, "altitude": 28.0},
                    "geoDataExif": {"latitude": 59.33, "longitude": 18.07},
                }
            )
        )

        result = parse_photos_metadata([f])
        assert len(result) == 1
        assert result[0]["title"] == "IMG_001.jpg"
        assert result[0]["latitude"] == 59.33
        assert result[0]["photo_taken_timestamp"] == "1711641600"

    def test_skips_album_metadata(self, tmp: Path) -> None:
        f = tmp / "metadata.json"
        f.write_text(json.dumps({"title": "Album", "description": ""}))
        assert parse_photos_metadata([f]) == []

    def test_skips_non_photo_json(self, tmp: Path) -> None:
        f = tmp / "random.json"
        f.write_text(json.dumps({"unrelated": True}))
        assert parse_photos_metadata([f]) == []


class TestLocationParser:
    def test_parses_records(self, tmp: Path) -> None:
        f = tmp / "Records.json"
        f.write_text(
            json.dumps(
                {
                    "locations": [
                        {
                            "timestamp": "2024-03-28T10:00:00Z",
                            "latitudeE7": 593300000,
                            "longitudeE7": 180700000,
                            "accuracy": 20,
                        }
                    ]
                }
            )
        )

        result = parse_location_records([f])
        assert len(result) == 1
        assert abs(result[0]["latitude"] - 59.33) < 0.001
        assert abs(result[0]["longitude"] - 18.07) < 0.001

    def test_parses_semantic_visits(self, tmp: Path) -> None:
        f = tmp / "2024_MARCH.json"
        f.write_text(
            json.dumps(
                {
                    "timelineObjects": [
                        {
                            "placeVisit": {
                                "location": {"name": "Office", "latitudeE7": 593300000, "longitudeE7": 180700000},
                                "duration": {"startTimestamp": "2024-03-28T08:00:00Z", "endTimestamp": "2024-03-28T17:00:00Z"},
                                "placeConfidence": "HIGH",
                            }
                        }
                    ]
                }
            )
        )

        result = parse_semantic_locations([f])
        assert len(result) == 1
        assert result[0]["type"] == "visit"
        assert result[0]["place_name"] == "Office"


class TestYouTubeParser:
    def test_parses_watch_history(self, tmp: Path) -> None:
        f = tmp / "watch-history.json"
        f.write_text(
            json.dumps(
                [
                    {
                        "title": "Watched a video",
                        "titleUrl": "https://youtube.com/watch?v=abc",
                        "time": "2024-03-28T12:00:00Z",
                        "subtitles": [{"name": "Channel Name", "url": "https://youtube.com/channel/xyz"}],
                        "header": "YouTube",
                    }
                ]
            )
        )

        result = parse_watch_history([f])
        assert len(result) == 1
        assert result[0]["title"] == "Watched a video"
        assert result[0]["channel_name"] == "Channel Name"

    def test_parses_search_history(self, tmp: Path) -> None:
        f = tmp / "search-history.json"
        f.write_text(
            json.dumps(
                [
                    {
                        "title": "Searched for python",
                        "titleUrl": "https://youtube.com/results?q=python",
                        "time": "2024-03-28T10:00:00Z",
                    }
                ]
            )
        )

        result = parse_search_history([f])
        assert len(result) == 1
        assert "python" in result[0]["title"]

    def test_parses_subscriptions(self, tmp: Path) -> None:
        f = tmp / "subscriptions.csv"
        f.write_text("Channel Id,Channel Url,Channel Title\nUC123,https://youtube.com/c/test,Test Channel\n")

        result = parse_subscriptions([f])
        assert len(result) == 1
        assert result[0]["channel_id"] == "UC123"
        assert result[0]["channel_title"] == "Test Channel"
