"""Parse Spotify streaming history export files (JSON).

Supports three export formats:
- Extended: endsong_*.json (full detail, from privacy data request)
- Current basic: Streaming_History_Audio_*.json
- Legacy basic: StreamingHistory*.json (4 fields, camelCase)
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt


def _find_history_files(export_dir: Path) -> list[Path]:
    """Find all streaming history JSON files in an export directory, sorted."""
    patterns = ["endsong_*.json", "Streaming_History_Audio_*.json", "StreamingHistory_music_*.json", "StreamingHistory*.json"]
    files: list[Path] = []
    seen: set[str] = set()
    for pattern in patterns:
        for f in sorted(export_dir.glob(pattern)):
            if f.name not in seen:
                files.append(f)
                seen.add(f.name)
    return sorted(files)


def _parse_extended(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Parse an endsong_*.json or Streaming_History_Audio_*.json entry."""
    track = entry.get("master_metadata_track_name")
    if not track:
        return None
    return {
        "played_at": entry.get("ts", ""),
        "track_name": track,
        "artist_name": entry.get("master_metadata_album_artist_name", ""),
        "album_name": entry.get("master_metadata_album_album_name", ""),
        "ms_played": entry.get("ms_played", 0),
        "spotify_track_uri": entry.get("spotify_track_uri"),
        "reason_start": entry.get("reason_start"),
        "reason_end": entry.get("reason_end"),
        "shuffle": entry.get("shuffle"),
        "skipped": entry.get("skipped"),
        "offline": entry.get("offline"),
        "platform": entry.get("platform"),
    }


def _parse_legacy(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a StreamingHistory*.json entry (legacy 4-field format)."""
    track = entry.get("trackName")
    if not track:
        return None
    end_time = entry.get("endTime", "")
    if end_time and "T" not in end_time:
        end_time = end_time.replace(" ", "T") + ":00Z"
    return {
        "played_at": end_time,
        "track_name": track,
        "artist_name": entry.get("artistName", ""),
        "album_name": "",
        "ms_played": entry.get("msPlayed", 0),
        "spotify_track_uri": None,
        "reason_start": None,
        "reason_end": None,
        "shuffle": None,
        "skipped": None,
        "offline": None,
        "platform": None,
    }


def _is_legacy(entry: dict[str, Any]) -> bool:
    """Check if an entry is legacy format (camelCase keys)."""
    return "trackName" in entry or "endTime" in entry


@dlt.resource(write_disposition="merge", primary_key=["played_at", "track_name"])
def streaming_history(export_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield streaming history entries from all JSON files in an export directory."""
    files = _find_history_files(export_dir)
    if not files:
        return

    for file_path in files:
        with open(file_path, encoding="utf-8") as f:
            entries = json.load(f)

        for entry in entries:
            if _is_legacy(entry):
                row = _parse_legacy(entry)
            else:
                row = _parse_extended(entry)
            if row:
                yield row
