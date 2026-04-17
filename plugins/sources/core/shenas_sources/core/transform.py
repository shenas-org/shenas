"""Transform utilities for sources."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any


def load_transform_defaults(source_name: str) -> list[dict[str, Any]]:
    """Load default transforms from a source's bundled transforms.json."""
    try:
        pkg = f"shenas_sources.{source_name}"
        ref = resources.files(pkg).joinpath("transforms.json")
        return json.loads(ref.read_text(encoding="utf-8"))
    except Exception:
        return []
