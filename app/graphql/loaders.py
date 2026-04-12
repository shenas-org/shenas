"""Strawberry dataloaders for batching GraphQL data fetches.

Created per-request via ``create_loaders()`` and injected into the
Strawberry context. This avoids N+1 queries for transforms, row
counts, and lineage lookups.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strawberry.dataloader import DataLoader

if TYPE_CHECKING:
    from app.data_catalog import DataResource


async def _load_resources(keys: list[str]) -> list[DataResource]:
    """Batch-load DataResource objects by ID.

    Uses the existing DataCatalog._resource_cache so the plugin walk
    only happens once per process, not once per request.
    """
    from app.data_catalog import catalog

    cat = catalog()
    return [cat.get_resource(k) for k in keys]


async def _load_row_counts(keys: list[str]) -> list[int | None]:
    """Batch COUNT(*) queries into a single UNION ALL."""
    from app.database import cursor

    if not keys:
        return []

    # Pre-filter to tables that actually exist
    with cursor() as cur:
        existing = {
            f"{r[0]}.{r[1]}" for r in cur.execute("SELECT table_schema, table_name FROM information_schema.tables").fetchall()
        }

    parts = []
    for k in keys:
        if k in existing:
            schema, table = k.split(".", 1)
            parts.append(f'SELECT \'{k}\' AS id, COUNT(*) AS cnt FROM "{schema}"."{table}"')

    if not parts:
        return [None] * len(keys)

    with cursor() as cur:
        rows = cur.execute(" UNION ALL ".join(parts)).fetchall()

    counts: dict[str, int] = {r[0]: r[1] for r in rows}
    return [counts.get(k) for k in keys]


async def _load_lineage(keys: list[str]) -> list[dict]:
    """Load all transforms once and partition by resource ID."""
    from shenas_transformers.core.transform import Transform

    all_transforms = Transform.all()
    result: dict[str, dict[str, list]] = {k: {"upstream": [], "downstream": []} for k in keys}

    for t in all_transforms:
        src = t.source_ref.id
        tgt = t.target_ref.id
        if tgt in result:
            result[tgt]["upstream"].append(t)
        if src in result:
            result[src]["downstream"].append(t)

    return [result.get(k, {"upstream": [], "downstream": []}) for k in keys]


def create_loaders() -> dict[str, DataLoader]:
    """Create fresh dataloaders for a single request."""
    return {
        "resource_loader": DataLoader(load_fn=_load_resources),
        "row_count_loader": DataLoader(load_fn=_load_row_counts),
        "lineage_loader": DataLoader(load_fn=_load_lineage),
    }
