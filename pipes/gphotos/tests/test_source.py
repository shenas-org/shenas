"""Tests for Google Photos source resources."""

from unittest.mock import MagicMock

from shenas_pipes.gphotos.source import albums, media_items


class TestMediaItems:
    def test_yields_photos(self) -> None:
        service = MagicMock()
        service.mediaItems().search().execute.return_value = {
            "mediaItems": [
                {
                    "id": "photo1",
                    "filename": "IMG_001.jpg",
                    "mimeType": "image/jpeg",
                    "mediaMetadata": {
                        "creationTime": "2026-03-28T10:00:00Z",
                        "width": "4032",
                        "height": "3024",
                        "photo": {"cameraMake": "Apple", "cameraModel": "iPhone 15"},
                    },
                }
            ]
        }

        result = list(media_items(service, start_date="2026-03-01"))
        assert len(result) == 1
        assert result[0]["id"] == "photo1"
        assert result[0]["media_type"] == "photo"
        assert result[0]["camera_make"] == "Apple"
        assert result[0]["width"] == 4032

    def test_yields_videos(self) -> None:
        service = MagicMock()
        service.mediaItems().search().execute.return_value = {
            "mediaItems": [
                {
                    "id": "vid1",
                    "filename": "VID_001.mp4",
                    "mimeType": "video/mp4",
                    "mediaMetadata": {
                        "creationTime": "2026-03-28T12:00:00Z",
                        "width": "1920",
                        "height": "1080",
                        "video": {"fps": 30.0},
                    },
                }
            ]
        }

        result = list(media_items(service, start_date="2026-03-01"))
        assert result[0]["media_type"] == "video"
        assert result[0]["fps"] == 30.0


class TestAlbums:
    def test_yields_albums(self) -> None:
        service = MagicMock()
        service.albums().list().execute.return_value = {
            "albums": [
                {
                    "id": "album1",
                    "title": "Vacation 2026",
                    "mediaItemsCount": "42",
                }
            ]
        }

        result = list(albums(service))
        assert len(result) == 1
        assert result[0]["id"] == "album1"
        assert result[0]["title"] == "Vacation 2026"
        assert result[0]["media_items_count"] == 42
