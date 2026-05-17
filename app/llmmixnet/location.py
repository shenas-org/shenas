"""Location coarsening for Layer 2 (ADR §4.3.4).

Production path: snap to H3 hex resolution 6 (~1 km edge length).
Fallback when the h3 package is not installed: truncate to 2 decimal
places (~1.1 km precision) so the behaviour degrades gracefully during
development. The fallback is not production-safe and is rejected at
runtime if h3 is unavailable and LLMMIXNET_REQUIRE_H3=1 is set.

Install h3 via: uv add h3 --package shenas-app
"""

from __future__ import annotations

import os
import re

H3_RESOLUTION = 6

_H3_AVAILABLE: bool | None = None


def _check_h3() -> bool:
    global _H3_AVAILABLE
    if _H3_AVAILABLE is None:
        try:
            import h3  # type: ignore[import-not-found]  # ty: ignore[unresolved-import]  # noqa: F401

            _H3_AVAILABLE = True
        except ImportError:
            _H3_AVAILABLE = False
    return _H3_AVAILABLE


def coarsen_coordinates(lat: float, lon: float) -> str:
    """Return a stable, coarsened location token for the given coordinates.

    When h3 is available: returns the H3 cell ID at resolution 6
    (~1 km edge), e.g. '87283472bffffff'.
    When h3 is unavailable: returns a truncated coordinate string
    at 2 decimal places, e.g. 'LOC_48.85_2.35'.
    """
    if _check_h3():
        import h3  # type: ignore[import-not-found]  # ty: ignore[unresolved-import]

        return h3.latlng_to_cell(lat, lon, H3_RESOLUTION)  # type: ignore[attr-defined]

    if os.environ.get("LLMMIXNET_REQUIRE_H3"):
        raise RuntimeError(
            "h3 package is required (LLMMIXNET_REQUIRE_H3 is set) but not installed. Run: uv add h3 --package shenas-app"
        )
    return f"LOC_{lat:.2f}_{lon:.2f}"


_COORD_PATTERN = re.compile(
    r"""
    [-+]?(?:\d+\.?\d*|\.\d+)   # latitude
    [,\s]+                       # separator
    [-+]?(?:\d+\.?\d*|\.\d+)   # longitude
    """,
    re.VERBOSE,
)


def extract_and_coarsen(location_text: str) -> str | None:
    """Extract lat/lon from a location string and return a coarsened token.

    Returns None when no coordinate pair is found (the caller falls back
    to the standard NER placeholder path).
    """
    match = _COORD_PATTERN.search(location_text)
    if match is None:
        return None
    parts = re.split(r"[,\s]+", match.group().strip())
    if len(parts) < 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None
    return coarsen_coordinates(lat, lon)
