"""Parse Google Fit data from Takeout exports."""

from __future__ import annotations

import contextlib
import csv
import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def _safe_float(value: str) -> float | None:
    """Convert a CSV value to float, returning None for empty/invalid."""
    if not value or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _safe_int(value: str) -> int | None:
    """Convert a CSV value to int, returning None for empty/invalid."""
    if not value or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        val = _safe_float(value)
        return int(val) if val is not None else None


# CSV column -> (output key, parser)
_DAILY_FLOAT_COLS = {
    "Calories (kcal)": "calories_kcal",
    "Distance (m)": "distance_m",
    "Heart Points": "heart_points",
    "Average heart rate (bpm)": "avg_heart_rate_bpm",
    "Max heart rate (bpm)": "max_heart_rate_bpm",
    "Average speed (m/s)": "avg_speed_ms",
    "Average weight (kg)": "weight_kg",
}

_DAILY_INT_COLS = {
    "Move Minutes count": "move_minutes",
    "Step count": "step_count",
    "Walking duration (ms)": "walking_duration_ms",
}


def parse_daily_metrics(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield 15-minute activity metric intervals from per-day CSV files.

    Each CSV file contains 15-minute intervals for one day. The date is
    derived from the filename, combined with the Start time column.
    """
    for path in files:
        if not path.name.endswith(".csv"):
            continue

        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
        if not date_match:
            continue
        date = date_match.group(1)

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        reader = csv.DictReader(text.splitlines())
        for row in reader:
            start_time = row.get("Start time", "")
            if not start_time:
                continue

            entry: dict[str, Any] = {"date": date, "start_time": f"{date}T{start_time}"}

            has_value = False
            for csv_col, output_key in _DAILY_FLOAT_COLS.items():
                val = _safe_float(row.get(csv_col, ""))
                entry[output_key] = val
                if val is not None:
                    has_value = True

            for csv_col, output_key in _DAILY_INT_COLS.items():
                val = _safe_int(row.get(csv_col, ""))
                entry[output_key] = val
                if val is not None:
                    has_value = True

            if has_value:
                yield entry


def parse_activity_sessions(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield activity sessions from the All Sessions JSON files."""
    for path in files:
        if not path.name.endswith(".json"):
            continue

        try:
            data = json.loads(path.read_bytes())
        except (json.JSONDecodeError, OSError):
            continue

        start_time = data.get("startTime", "")
        if not start_time:
            continue

        duration_str = data.get("duration", "")
        duration_s: int | None = None
        if duration_str and duration_str.endswith("s"):
            with contextlib.suppress(ValueError):
                duration_s = int(float(duration_str[:-1]))

        aggregates = _extract_aggregates(data.get("aggregate", []))

        yield {
            "activity": data.get("fitnessActivity", "unknown"),
            "start_time": start_time,
            "end_time": data.get("endTime", ""),
            "duration_s": duration_s,
            **aggregates,
        }


_AGGREGATE_MAP = {
    "com.google.calories.expended": ("calories_kcal", "float"),
    "com.google.step_count.delta": ("step_count", "int"),
    "com.google.distance.delta": ("distance_m", "float"),
    "com.google.speed.summary": ("avg_speed_ms", "float"),
}


def _extract_aggregates(aggregates: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract known aggregate metrics from a Fit session."""
    result: dict[str, Any] = {key: None for key, _ in _AGGREGATE_MAP.values()}
    for agg in aggregates:
        metric = agg.get("metricName", "")
        mapping = _AGGREGATE_MAP.get(metric)
        if not mapping:
            continue
        output_key, value_type = mapping
        if value_type == "float":
            val = agg.get("floatValue")
            result[output_key] = round(val, 1) if val else None
        else:
            result[output_key] = agg.get("intValue")
    return result
