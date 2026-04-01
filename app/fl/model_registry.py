"""Model plugin registry.

Model plugins register via the `shenas.models` entry point group.
Each plugin module must export a MODEL dict with:
  - name: str
  - description: str
  - model_cls: a callable(n_features) -> nn.Module
  - features: list[str] -- metric columns used as input
  - target: str -- metric column to predict
  - query: str -- SQL to fetch training data
"""

from __future__ import annotations

import importlib.metadata
import logging
from typing import Any

logger = logging.getLogger(__name__)

_cache: dict[str, dict[str, Any]] | None = None


def discover_models() -> dict[str, dict[str, Any]]:
    """Discover all installed model plugins via entry points."""
    global _cache
    if _cache is not None:
        return _cache

    models: dict[str, dict[str, Any]] = {}
    for ep in importlib.metadata.entry_points(group="shenas.models"):
        try:
            mod = ep.load()
            meta = getattr(mod, "MODEL", None)
            if isinstance(meta, dict) and "name" in meta:
                models[meta["name"]] = meta
                logger.debug("Discovered model plugin: %s", meta["name"])
        except Exception:
            logger.warning("Failed to load model plugin: %s", ep.name, exc_info=True)

    _cache = models
    return models


def get_model_meta(name: str) -> dict[str, Any] | None:
    """Get metadata for a specific model plugin."""
    return discover_models().get(name)


def list_model_names() -> list[str]:
    """List all discovered model plugin names."""
    return list(discover_models().keys())
