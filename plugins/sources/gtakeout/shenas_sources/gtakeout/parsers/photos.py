"""Parse Google Photos metadata from Takeout exports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def parse_photos_metadata(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield photo/video metadata from Google Photos Takeout JSON files."""
    for f in files:
        if not f.name.endswith(".json") or f.name == "metadata.json":
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if "title" not in data and "photoTakenTime" not in data:
            continue

        geo = data.get("geoData", {})
        geo_exif = data.get("geoDataExif", {})
        photo_taken = data.get("photoTakenTime", {})
        creation = data.get("creationTime", {})

        yield {
            "title": data.get("title", ""),
            "photo_description": data.get("description", ""),
            "photo_taken_timestamp": photo_taken.get("timestamp", ""),
            "photo_taken_formatted": photo_taken.get("formatted", ""),
            "creation_timestamp": creation.get("timestamp", ""),
            "creation_formatted": creation.get("formatted", ""),
            "latitude": geo.get("latitude", 0.0),
            "longitude": geo.get("longitude", 0.0),
            "altitude": geo.get("altitude", 0.0),
            "latitude_exif": geo_exif.get("latitude", 0.0),
            "longitude_exif": geo_exif.get("longitude", 0.0),
            "camera_make": data.get("googlePhotosOrigin", {}).get("mobileUpload", {}).get("deviceType", ""),
            "url": data.get("url", ""),
            "source_file": f.name,
        }
