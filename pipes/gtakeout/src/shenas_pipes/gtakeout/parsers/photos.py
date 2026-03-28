"""Parse Google Photos metadata from Takeout exports."""

import json
from pathlib import Path
from typing import Any


def parse_photos_metadata(files: list[Path]) -> list[dict[str, Any]]:
    """Parse photo/video metadata JSON files from Google Photos Takeout."""
    items = []
    for f in files:
        if not f.name.endswith(".json"):
            continue
        # Skip the metadata.json album files
        if f.name == "metadata.json":
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        # Google Photos metadata JSON has a specific structure
        if "title" not in data and "photoTakenTime" not in data:
            continue

        geo = data.get("geoData", {})
        geo_exif = data.get("geoDataExif", {})
        photo_taken = data.get("photoTakenTime", {})
        creation = data.get("creationTime", {})

        items.append(
            {
                "title": data.get("title", ""),
                "description": data.get("description", ""),
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
                "source_file": str(f.relative_to(f.parents[2]) if len(f.parents) > 2 else f.name),
            }
        )

    return items
