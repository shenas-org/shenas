"""LLM categorization transformation plugin."""

from __future__ import annotations

import contextlib
import hashlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

import duckdb
from shenas_transformations.core import Transformation, TransformationConfig

from shenas_plugins.core.table import Field

if TYPE_CHECKING:
    from shenas_transformations.core.instance import TransformInstance

log = logging.getLogger(f"shenas.{__name__}")


@dataclass
class _LlmConfig(TransformationConfig):
    api_key: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="Anthropic API key",
            category="secret",
            ui_widget="password",
        ),
    ] = None
    model: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Model name",
            db_default="'claude-sonnet-4-20250514'",
        ),
    ] = "claude-sonnet-4-20250514"


class LlmCategorizeTransformation(Transformation):
    """Use an LLM to categorize or enrich data."""

    name = "llm-categorize"
    display_name = "LLM Categorize Transform"
    description = "Use an LLM to categorize or enrich data (e.g., categorize transaction descriptions)."

    Config = _LlmConfig

    def execute(
        self,
        con: duckdb.DuckDBPyConnection,
        instance: TransformInstance,
        *,
        device_id: str = "local",
    ) -> int:
        params = instance.get_params()
        text_col = params.get("text_column")
        if not text_col:
            log.warning("LLM transform #%d missing text_column param", instance.id)
            return 0

        output_col = params.get("output_column", "category")
        categories = params.get("categories", "")
        prompt_template = params.get("prompt", "Categorize the following text into one word: {text}")
        source_name = instance.source_plugin
        source = f'"{instance.source_duckdb_schema}"."{instance.source_duckdb_table}"'
        target = f'"{instance.target_duckdb_schema}"."{instance.target_duckdb_table}"'

        try:
            con.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])

            # Ensure LLM cache table
            con.execute("""
                CREATE TABLE IF NOT EXISTS shenas_system.llm_cache (
                    content_hash VARCHAR PRIMARY KEY,
                    input_text VARCHAR,
                    result VARCHAR,
                    model VARCHAR,
                    prompt_hash VARCHAR,
                    created_at TIMESTAMP DEFAULT current_timestamp
                )
            """)

            config = self.Config.read_row() or {}
            api_key = config.get("api_key")
            model = config.get("model", "claude-sonnet-4-20250514")

            if not api_key:
                log.warning("LLM transform #%d: no API key configured", instance.id)
                return 0

            # Read distinct text values
            rows = con.execute(
                f"SELECT DISTINCT {text_col} AS txt FROM {source} WHERE {text_col} IS NOT NULL AND TRIM({text_col}) != ''"
            ).fetchall()

            texts = [r[0] for r in rows]
            prompt_hash = hashlib.sha256(prompt_template.encode()).hexdigest()[:16]

            # Check cache
            cached: dict[str, str] = {}
            for txt in texts:
                content_hash = hashlib.sha256(txt.encode()).hexdigest()[:16]
                result = con.execute(
                    "SELECT result FROM shenas_system.llm_cache WHERE content_hash = ? AND prompt_hash = ?",
                    [content_hash, prompt_hash],
                ).fetchone()
                if result:
                    cached[txt] = result[0]

            # Categorize uncached
            uncached = [t for t in texts if t not in cached]
            if uncached:
                categorized = _batch_categorize(
                    uncached,
                    prompt_template=prompt_template,
                    categories=categories,
                    api_key=api_key,
                    model=model,
                )
                for txt, cat in categorized.items():
                    content_hash = hashlib.sha256(txt.encode()).hexdigest()[:16]
                    con.execute(
                        "INSERT OR REPLACE INTO shenas_system.llm_cache "
                        "(content_hash, input_text, result, model, prompt_hash) "
                        "VALUES (?, ?, ?, ?, ?)",
                        [content_hash, txt, cat, model, prompt_hash],
                    )
                    cached[txt] = cat

            # Write: join source with cached results
            with contextlib.suppress(duckdb.Error):
                con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

            con.execute(
                f"INSERT INTO {target} "
                f"SELECT s.*, lc.result AS {output_col}, '{device_id}' AS source_device "
                f"FROM {source} s "
                f"LEFT JOIN shenas_system.llm_cache lc "
                f"ON SHA256(s.{text_col})[:16] = lc.content_hash "
                f"AND lc.prompt_hash = '{prompt_hash}'"
            )
            return 1
        except Exception:
            log.exception("LLM transform #%d failed (%s -> %s)", instance.id, source_name, target)
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {"name": "text_column", "type": "text", "required": True, "description": "Column containing text to categorize"},
            {
                "name": "output_column",
                "type": "text",
                "required": False,
                "description": "Output column name for the category",
                "default": "category",
            },
            {
                "name": "categories",
                "type": "text",
                "required": False,
                "description": "Comma-separated list of valid categories",
            },
            {
                "name": "prompt",
                "type": "textarea",
                "required": False,
                "description": "Prompt template ({text} is replaced with the value)",
            },
        ]

    def validate_params(self, params: dict[str, Any]) -> None:
        if not params.get("text_column"):
            msg = "text_column is required"
            raise ValueError(msg)


def _batch_categorize(
    texts: list[str],
    *,
    prompt_template: str,
    categories: str,
    api_key: str,
    model: str,
) -> dict[str, str]:
    """Categorize texts via the Anthropic API. Returns {text: category}."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    results: dict[str, str] = {}

    category_hint = ""
    if categories:
        category_hint = f" Valid categories: {categories}."

    for text in texts:
        prompt = prompt_template.replace("{text}", text) + category_hint
        try:
            response = client.messages.create(
                model=model,
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.content[0].text.strip()
            results[text] = result
        except Exception:
            log.warning("LLM categorization failed for '%s'", text[:50])

    return results


__all__ = ["LlmCategorizeTransformation"]
