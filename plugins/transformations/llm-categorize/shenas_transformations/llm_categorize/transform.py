"""LLM categorization transform -- thin consumer of app.llm."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any

import duckdb
from shenas_transformations.core import Transform, TransformConfig

from app.llm import Backend, LlmCache
from shenas_plugins.core.table import Field

if TYPE_CHECKING:
    from shenas_transformations.core.instance import TransformInstance

log = logging.getLogger(f"shenas.{__name__}")


@dataclass
class _LlmConfig(TransformConfig):
    backend: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="LLM backend: local | proxy",
            db_default="'local'",
        ),
    ] = "local"
    model_path: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="GGUF filename in ~/.shenas/models/, or absolute path (backend=local)",
        ),
    ] = None
    proxy_model: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Cloud model served by shenas.net (backend=proxy)",
            db_default="'claude-sonnet-4-6'",
        ),
    ] = "claude-sonnet-4-6"


class LlmCategorizeTransform(Transform):
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
        prompt_template = params.get("prompt", "Categorize the following text into one word: {text}")
        categories = params.get("categories", "")
        source_name = instance.source_plugin
        source = f'"{instance.source_duckdb_schema}"."{instance.source_duckdb_table}"'
        target = f'"{instance.target_duckdb_schema}"."{instance.target_duckdb_table}"'

        try:
            config = self.Config.read_row() or {}
            backend = Backend.from_config(config)
            cache = LlmCache(con)

            con.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])

            rows = con.execute(
                f"SELECT DISTINCT {text_col} AS txt FROM {source} WHERE {text_col} IS NOT NULL AND TRIM({text_col}) != ''"
            ).fetchall()
            texts = [r[0] for r in rows]

            category_hint = f" Valid categories: {categories}." if categories else ""
            prompt_hash = LlmCache.hash16(prompt_template + category_hint)

            for text in texts:
                if cache.get(text=text, prompt_hash=prompt_hash, model=backend.name):
                    continue
                prompt = prompt_template.replace("{text}", text) + category_hint
                result = backend.categorize(text, prompt=prompt)
                if result is not None:
                    cache.put(text=text, prompt_hash=prompt_hash, model=backend.name, result=result)

            with contextlib.suppress(duckdb.Error):
                con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

            con.execute(
                f"INSERT INTO {target} "
                + cache.join_sql(
                    source=source,
                    text_col=text_col,
                    prompt_hash=prompt_hash,
                    model=backend.name,
                    output_col=output_col,
                )
                + f", '{device_id}' AS source_device"
            )
            return 1
        except Exception:
            log.exception("LLM transform #%d failed (%s -> %s)", instance.id, source_name, target)
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "text_column",
                "label": "Text column",
                "type": "source_column",
                "required": True,
                "description": "Column containing text to categorize",
            },
            {
                "name": "output_column",
                "label": "Target column",
                "type": "target_column",
                "required": False,
                "description": "Column name for the category in the target table",
                "default": "category",
            },
            {
                "name": "categories",
                "label": "Categories",
                "type": "text",
                "required": False,
                "description": "Comma-separated list of valid categories",
            },
            {
                "name": "prompt",
                "label": "Prompt template",
                "type": "textarea",
                "required": False,
                "description": "Prompt template ({text} is replaced with the value)",
            },
        ]

    def validate_params(self, params: dict[str, Any]) -> None:
        if not params.get("text_column"):
            msg = "text_column is required"
            raise ValueError(msg)
