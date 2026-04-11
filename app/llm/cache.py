"""DuckDB-backed LLM response cache."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb


class LlmCache:
    """Thin wrapper around shenas_system.llm_cache."""

    TABLE = "shenas_system.llm_cache"

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.con.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE} (
                content_hash VARCHAR,
                input_text VARCHAR,
                result VARCHAR,
                model VARCHAR,
                prompt_hash VARCHAR,
                created_at TIMESTAMP DEFAULT current_timestamp,
                PRIMARY KEY (content_hash, prompt_hash, model)
            )
        """)

    @staticmethod
    def hash16(s: str) -> str:
        return hashlib.sha256(s.encode()).hexdigest()[:16]

    def get(self, *, text: str, prompt_hash: str, model: str) -> str | None:
        row = self.con.execute(
            f"SELECT result FROM {self.TABLE} WHERE content_hash = ? AND prompt_hash = ? AND model = ?",
            [self.hash16(text), prompt_hash, model],
        ).fetchone()
        return row[0] if row else None

    def put(self, *, text: str, prompt_hash: str, model: str, result: str) -> None:
        self.con.execute(
            f"INSERT OR REPLACE INTO {self.TABLE} "
            "(content_hash, input_text, result, model, prompt_hash) VALUES (?, ?, ?, ?, ?)",
            [self.hash16(text), text, result, model, prompt_hash],
        )

    def join_sql(self, *, source: str, text_col: str, prompt_hash: str, model: str, output_col: str) -> str:
        """Build the SELECT that joins a source table to its cached results."""
        return (
            f"SELECT s.*, lc.result AS {output_col} "
            f"FROM {source} s LEFT JOIN {self.TABLE} lc "
            f"ON SHA256(s.{text_col})[:16] = lc.content_hash "
            f"AND lc.prompt_hash = '{prompt_hash}' "
            f"AND lc.model = '{model}'"
        )
