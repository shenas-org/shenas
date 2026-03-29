"""Transform utilities for pipes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_transform_defaults(pipe_name: str) -> list[dict[str, Any]]:
    """Load default transforms from a pipe's transforms.json file."""
    try:
        import importlib

        mod = importlib.import_module(f"shenas_pipes.{pipe_name}")
        mod_dir = Path(mod.__file__).parent if mod.__file__ else None
        if not mod_dir:
            return []
        json_path = mod_dir.parent.parent.parent / "transforms.json"
        if not json_path.exists():
            return []
        return json.loads(json_path.read_text())
    except Exception:
        return []
