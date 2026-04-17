"""Regex extract transformation -- pattern matching on text columns."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import duckdb
from shenas_transformers.core import Transformer

if TYPE_CHECKING:
    from shenas_transformers.core.transform import Transform


class RegexExtractTransformer(Transformer):
    """Extract or replace text using regular expressions.

    Supports two modes:
    - **extract**: Pull a named group or first capture group from a column
    - **replace**: Apply regexp_replace to normalize/clean a column
    """

    name = "regex-extract"
    display_name = "Regex Extract Transformer"
    description = "Extract or replace text in columns using regular expressions."

    def execute(
        self,
        instance: Transform,
        *,
        device_id: str = "local",
    ) -> int:
        params = instance.get_params()
        text_col = params.get("text_column")
        if not text_col:
            self.log.warning("Regex transform #%d missing text_column param", instance.id)
            return 0

        pattern = params.get("pattern", "")
        if not pattern:
            self.log.warning("Regex transform #%d missing pattern param", instance.id)
            return 0

        output_col = params.get("output_column", f"{text_col}_extracted")
        mode = params.get("mode", "extract")
        replacement = params.get("replacement", "\\1")
        source_name = instance.source_plugin
        source = f'"{instance.source_ref.schema}"."{instance.source_ref.table}"'
        target = f'"{instance.target_ref.schema}"."{instance.target_ref.table}"'

        try:
            from app.database import cursor

            if mode == "replace":
                expr = f"regexp_replace({text_col}, '{pattern}', '{replacement}', 'g')"
            else:
                expr = f"regexp_extract({text_col}, '{pattern}', 1)"

            with cursor() as cur:
                cur.execute(f"DELETE FROM {target} WHERE source = ?", [source_name])
                with contextlib.suppress(duckdb.Error):
                    cur.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")
                cur.execute(
                    f"INSERT INTO {target} SELECT s.*, {expr} AS {output_col}, '{device_id}' AS source_device FROM {source} s"
                )
            return 1
        except Exception:
            self.log.exception(
                "Regex transform #%d failed (%s -> %s)",
                instance.id,
                source_name,
                target,
            )
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "text_column",
                "label": "Text column",
                "type": "text",
                "required": True,
                "description": "Column containing text to match against",
            },
            {
                "name": "pattern",
                "label": "Regex pattern",
                "type": "text",
                "required": True,
                "description": "Regular expression pattern (use capture groups for extract mode)",
            },
            {
                "name": "output_column",
                "label": "Output column",
                "type": "text",
                "required": False,
                "description": "Output column name",
                "default": "{text_column}_extracted",
            },
            {
                "name": "mode",
                "label": "Mode",
                "type": "select",
                "required": False,
                "description": "Mode: extract (capture group) or replace (substitution)",
                "default": "extract",
                "options": ["extract", "replace"],
            },
            {
                "name": "replacement",
                "label": "Replacement string",
                "type": "text",
                "required": False,
                "description": "Replacement string for replace mode (supports \\1 backreferences)",
                "default": "\\1",
            },
        ]

    def validate_params(self, params: dict[str, Any]) -> None:
        if not params.get("text_column"):
            msg = "text_column is required"
            raise ValueError(msg)
        if not params.get("pattern"):
            msg = "pattern is required"
            raise ValueError(msg)


__all__ = ["RegexExtractTransform"]
