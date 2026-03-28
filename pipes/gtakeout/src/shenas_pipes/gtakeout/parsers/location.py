"""Parse Location History from Takeout exports."""

import json
from pathlib import Path
from typing import Any


def parse_location_records(files: list[Path]) -> list[dict[str, Any]]:
    """Parse location records from Records.json."""
    items = []
    for f in files:
        if f.name != "Records.json":
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for loc in data.get("locations", []):
            items.append(
                {
                    "timestamp": loc.get("timestamp", ""),
                    "latitude": loc.get("latitudeE7", 0) / 1e7,
                    "longitude": loc.get("longitudeE7", 0) / 1e7,
                    "accuracy": loc.get("accuracy", 0),
                    "altitude": loc.get("altitude", 0),
                    "source": loc.get("source", ""),
                    "device_tag": loc.get("deviceTag", ""),
                }
            )

    return items


def parse_semantic_locations(files: list[Path]) -> list[dict[str, Any]]:
    """Parse Semantic Location History (place visits and activity segments)."""
    visits = []
    for f in files:
        if not f.name.endswith(".json"):
            continue

        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for obj in data.get("timelineObjects", []):
            visit = obj.get("placeVisit")
            if visit:
                location = visit.get("location", {})
                duration = visit.get("duration", {})
                visits.append(
                    {
                        "type": "visit",
                        "place_name": location.get("name", ""),
                        "place_address": location.get("address", ""),
                        "place_id": location.get("placeId", ""),
                        "latitude": location.get("latitudeE7", 0) / 1e7,
                        "longitude": location.get("longitudeE7", 0) / 1e7,
                        "start_timestamp": duration.get("startTimestamp", ""),
                        "end_timestamp": duration.get("endTimestamp", ""),
                        "confidence": visit.get("placeConfidence", ""),
                    }
                )

            segment = obj.get("activitySegment")
            if segment:
                duration = segment.get("duration", {})
                start_loc = segment.get("startLocation", {})
                visits.append(
                    {
                        "type": "activity",
                        "place_name": segment.get("activityType", ""),
                        "place_address": "",
                        "place_id": "",
                        "latitude": start_loc.get("latitudeE7", 0) / 1e7,
                        "longitude": start_loc.get("longitudeE7", 0) / 1e7,
                        "start_timestamp": duration.get("startTimestamp", ""),
                        "end_timestamp": duration.get("endTimestamp", ""),
                        "confidence": segment.get("confidence", ""),
                    }
                )

    return visits
