"""Content-hash keyed cache of recipe results.

A user may re-run the same hypothesis many times during exploration.
For deterministic recipes over unchanged inputs that's wasted work, so
we cache results keyed by:

    sha256(recipe_json + sorted(input_table → max(_dlt_loaded_at) per input))

Any change to the recipe OR to any input table's last-load timestamp
produces a new key, which forces a re-execution. Tables that lack
``_dlt_loaded_at`` (system tables, hand-built canonical metrics)
contribute the literal string ``"static"`` so they don't accidentally
bust the cache forever.

Storage is one row per cache entry in ``analysis.recipe_cache``.
The ``RecipeCache`` class IS the API: ``key_for`` builds the hash,
``find`` (from the ABC) reads, ``put`` writes, ``clear_rows`` (from
the ABC) drops everything.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from app.table import Field, Table


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass  # redundant at runtime (Table.__init_subclass__ re-applies it) but ty needs it to see the synthetic __init__
class RecipeCache(Table):
    """One row per cached recipe execution.

    Generic CRUD (``find`` / ``all`` / ``insert`` / ``save`` / ``upsert``
    / ``clear_rows``) comes from the :class:`Table` ABC. Cache-specific
    helpers live as methods here so the class is the whole API.
    """

    class _Meta:
        name = "recipe_cache"
        display_name = "Recipe Cache"
        description = "Content-hash keyed cache of recipe execution results."
        schema = "analysis"
        pk = ("cache_key",)

    cache_key: Annotated[str, Field(db_type="VARCHAR", description="sha256(recipe + freshness)")] = ""
    result_json: Annotated[str, Field(db_type="TEXT", description="Serialized Result tagged union")] = ""
    created_at: (
        Annotated[
            str,
            Field(db_type="TIMESTAMP", description="When this entry was minted", db_default="current_timestamp"),
        ]
        | None
    ) = None

    @property
    def payload(self) -> dict[str, Any] | None:
        """Decode ``result_json`` to a dict, or ``None`` on empty / parse error."""
        if not self.result_json:
            return None
        try:
            return json.loads(self.result_json)
        except Exception:
            return None

    @classmethod
    def key_for(cls, recipe_json: str, input_tables: list[str]) -> str:
        """Deterministic cache key for one recipe + its inputs.

        Combines the recipe text with each input table's freshness
        marker so a re-load on any input invalidates the cache entry.
        """
        parts = [recipe_json, *(f"{t}@{cls._freshness_for(t)}" for t in sorted(set(input_tables)))]
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()

    @classmethod
    def put(cls, key: str, payload: dict[str, Any]) -> None:
        """Upsert one cache entry."""
        cls(cache_key=key, result_json=json.dumps(payload), created_at=_now_iso()).upsert()

    @classmethod
    def _freshness_for(cls, qualified_table: str) -> str:
        """Return a cache-busting marker for one input table.

        For dlt-managed tables we read ``max(_dlt_loaded_at)``; for
        anything else we return ``"static"`` so the cache key stays
        stable across runs.
        """
        from app.database import cursor

        schema, _, table = qualified_table.partition(".")
        if not table:
            return "unknown"
        safe_schema = schema.replace('"', '""')
        safe_table = table.replace('"', '""')
        try:
            with cursor() as cur:
                row = cur.execute(f'SELECT max("_dlt_loaded_at")::VARCHAR FROM "{safe_schema}"."{safe_table}"').fetchone()
            return (row[0] if row and row[0] else "empty") or "empty"
        except Exception:
            return "static"
