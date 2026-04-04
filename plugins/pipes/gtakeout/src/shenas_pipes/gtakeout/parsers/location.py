"""Parse Location History from Takeout exports (streaming with ijson)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import ijson

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def parse_location_records(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield location records from Records.json (streamed, constant memory)."""
    for f in files:
        if f.name != "Records.json":
            continue

        with open(f, "rb") as fh:
            for loc in ijson.items(fh, "locations.item"):
                yield {
                    "timestamp": loc.get("timestamp", ""),
                    "latitude": loc.get("latitudeE7", 0) / 1e7,
                    "longitude": loc.get("longitudeE7", 0) / 1e7,
                    "accuracy": loc.get("accuracy", 0),
                    "altitude": loc.get("altitude", 0),
                    "source": loc.get("source", ""),
                    "device_tag": loc.get("deviceTag", ""),
                }


def parse_semantic_locations(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield semantic location visits/activities (streamed)."""
    for f in files:
        if not f.name.endswith(".json"):
            continue

        with open(f, "rb") as fh:
            for obj in ijson.items(fh, "timelineObjects.item"):
                visit = obj.get("placeVisit")
                if visit:
                    location = visit.get("location", {})
                    duration = visit.get("duration", {})
                    yield {
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

                segment = obj.get("activitySegment")
                if segment:
                    duration = segment.get("duration", {})
                    start_loc = segment.get("startLocation", {})
                    yield {
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
