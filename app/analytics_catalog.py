"""Shared catalog walker for the analytics layer.

Both the GraphQL ``catalog`` query (which serves the LLM with a flat
list of every queryable table) and the recipe runner (which expects a
dict keyed by qualified table name for kind / time-axis lookups) walk
the same plugin set: every installed source's ``TABLES`` tuple plus
every installed dataset's ``all_tables`` ClassVar. This module is the
single source of truth for that walk; the two consumers re-shape its
output to taste.
"""

from __future__ import annotations

from typing import Any


def _walk_sources() -> list[dict[str, Any]]:
    """Return ``[table_metadata]`` for source tables only."""
    import importlib

    from app.api.sources import _load_plugins
    from shenas_plugins.core.plugin import Plugin

    out: list[dict[str, Any]] = []
    for src_cls in _load_plugins("source", base=Plugin, include_internal=False):
        try:
            tables_mod = importlib.import_module(f"shenas_sources.{src_cls.name}.tables")
        except ImportError:
            continue
        out.extend(t.table_metadata() for t in getattr(tables_mod, "TABLES", ()))
    return out


def _walk_metrics() -> list[dict[str, Any]]:
    """Return ``[table_metadata]`` for metric tables only (code-based + data-defined)."""
    from app.api.sources import _load_datasets
    from shenas_datasets.core import Dataset
    from shenas_plugins.core.plugin import PluginInstance

    out: list[dict[str, Any]] = []
    # Code-based datasets
    for dataset_cls in _load_datasets():
        out.extend(t.table_metadata() for t in getattr(dataset_cls, "all_tables", ()))
    # Data-defined datasets (accepted PluginInstances with metadata)
    where = (
        "kind = 'dataset'"
        " AND (is_suggested IS NULL OR is_suggested = FALSE)"
        " AND metadata_json IS NOT NULL AND metadata_json != ''"
    )
    for pi in PluginInstance.all(where=where, order_by="name"):
        out.extend(Dataset.suggested_metadata(pi))
    return out


def walk_source_catalog() -> list[dict[str, Any]]:
    """Source tables only. Used by dataset suggestion LLM prompt."""
    return _walk_sources()


def walk_metrics_catalog() -> list[dict[str, Any]]:
    """Metric tables only (code-based + data-defined). Used by analysis suggestion LLM prompt."""
    return _walk_metrics()


def walk_catalog() -> list[dict[str, Any]]:
    """Return ``[table_metadata]`` for every installed source / metric table.

    System tables (Hypothesis, Transform, Hotkey, Workspace,
    PluginInstance, ...) are intentionally excluded -- they are not
    joinable analytical inputs.
    """
    return _walk_sources() + _walk_metrics()


def catalog_by_qualified_name() -> dict[str, dict[str, Any]]:
    """Return ``{"<schema>.<table>": table_metadata}`` over the full walk.

    The recipe runner expects this shape so it can look a SourceRef's
    qualified name up directly. Schemas that come back ``None`` from a
    metric table fall back to ``"metrics"``.
    """
    return {f"{m['schema'] or 'metrics'}.{m['table']}": m for m in walk_catalog()}
