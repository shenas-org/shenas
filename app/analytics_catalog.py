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


def walk_catalog() -> list[dict[str, Any]]:
    """Return ``[table_metadata]`` for every installed source / metric table.

    System tables (Hypothesis, Transform, Hotkey, Workspace,
    PluginInstance, ...) are intentionally excluded -- they are not
    joinable analytical inputs.
    """
    import importlib

    from app.api.sources import _load_datasets, _load_plugins
    from shenas_plugins.core.plugin import Plugin

    out: list[dict[str, Any]] = []
    for src_cls in _load_plugins("source", base=Plugin, include_internal=False):
        try:
            tables_mod = importlib.import_module(f"shenas_sources.{src_cls.name}.tables")
        except ImportError:
            continue
        out.extend(t.table_metadata() for t in getattr(tables_mod, "TABLES", ()))
    for dataset_cls in _load_datasets():
        out.extend(t.table_metadata() for t in getattr(dataset_cls, "all_tables", ()))
    return out


def catalog_by_qualified_name() -> dict[str, dict[str, Any]]:
    """Return ``{"<schema>.<table>": table_metadata}`` over the full walk.

    The recipe runner expects this shape so it can look a SourceRef's
    qualified name up directly. Schemas that come back ``None`` from a
    metric table fall back to ``"metrics"``.
    """
    return {f"{m['schema'] or 'metrics'}.{m['table']}": m for m in walk_catalog()}
