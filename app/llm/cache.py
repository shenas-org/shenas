"""DuckDB-backed LLM response cache."""

from __future__ import annotations

import hashlib
from typing import Annotated

from app.schema import CACHE
from app.table import Field, Table


class LlmCacheEntry(Table):
    """A cached LLM response keyed on (content_hash, prompt_hash, model).

    The Table subclass provides DDL (``ensure``) and schema introspection.
    :class:`LlmCache` wraps it with a convenience API (``get`` / ``put``).
    """

    class _Meta:
        name = "llm_cache"
        display_name = "LLM Cache"
        description = "Cached LLM responses for deterministic re-use."
        schema = CACHE
        pk = ("content_hash", "prompt_hash", "model")

    content_hash: Annotated[str, Field(db_type="VARCHAR", description="SHA-256 prefix of input text")] = ""
    input_text: Annotated[str, Field(db_type="VARCHAR", description="Original input text")] = ""
    result: Annotated[str, Field(db_type="VARCHAR", description="LLM response")] = ""
    model: Annotated[str, Field(db_type="VARCHAR", description="Model identifier")] = ""
    prompt_hash: Annotated[str, Field(db_type="VARCHAR", description="Hash of the system prompt")] = ""
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="When cached", db_default="current_timestamp")
    ] = None


class LlmCache:
    """Convenience wrapper around :class:`LlmCacheEntry`."""

    TABLE = "cache.llm_cache"

    def __init__(self) -> None:
        LlmCacheEntry.ensure()

    @staticmethod
    def hash16(s: str) -> str:
        return hashlib.sha256(s.encode()).hexdigest()[:16]

    def get(self, *, text: str, prompt_hash: str, model: str) -> str | None:
        entry = LlmCacheEntry.find(self.hash16(text), prompt_hash, model)
        return entry.result if entry else None

    def put(self, *, text: str, prompt_hash: str, model: str, result: str) -> None:
        h = self.hash16(text)
        existing = LlmCacheEntry.find(h, prompt_hash, model)
        if existing is None:
            LlmCacheEntry.from_row((h, text, result, model, prompt_hash, None)).insert()
        else:
            existing.result = result
            existing.input_text = text
            existing.save()

    def join_sql(self, *, source: str, text_col: str, prompt_hash: str, model: str, output_col: str) -> tuple[str, list[str]]:
        """Build the SELECT that joins a source table to its cached results.

        Returns ``(sql, params)`` so values are parametrized, not interpolated.
        """
        sql = (
            f"SELECT s.*, lc.result AS {output_col} "
            f"FROM {source} s LEFT JOIN {self.TABLE} lc "
            f"ON SHA256(s.{text_col})[:16] = lc.content_hash "
            "AND lc.prompt_hash = ? "
            "AND lc.model = ?"
        )
        return sql, [prompt_hash, model]
