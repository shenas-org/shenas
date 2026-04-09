"""SQL transformation plugin -- executes arbitrary SQL transforms."""

from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

import duckdb
from shenas_transformations.core import Transformation
from shenas_transformations.core.instance import TransformInstance

log = logging.getLogger(f"shenas.{__name__}")


class SqlTransformation(Transformation):
    """Execute arbitrary SQL to transform source data into target tables."""

    name = "sql"
    display_name = "SQL Transform"
    description = "Execute arbitrary SQL to transform source data into target tables."
    internal = True

    def execute(
        self,
        con: duckdb.DuckDBPyConnection,
        instance: TransformInstance,
        *,
        device_id: str = "local",
    ) -> int:
        params = instance.get_params()
        sql = params.get("sql", "")
        if not sql:
            log.warning("Transform #%d has no SQL in params", instance.id)
            return 0

        target = f'"{instance.target_duckdb_schema}"."{instance.target_duckdb_table}"'
        try:
            con.execute(f"DELETE FROM {target} WHERE source = ?", [instance.source_plugin])

            from app.db import cursor

            with cursor() as cur:
                cur.execute(f"SELECT * FROM ({sql}) _t LIMIT 0")
                cols = [d[0] for d in cur.description]

            col_names = ", ".join(f'"{c}"' for c in cols)

            with contextlib.suppress(duckdb.Error):
                con.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

            col_names_with_device = col_names + ', "source_device"'
            sql_with_device = f"SELECT *, '{device_id}' as source_device FROM ({sql}) _t"
            con.execute(f"INSERT INTO {target} ({col_names_with_device}) {sql_with_device}")
            return 1
        except Exception:
            log.exception("Transform #%d failed (%s -> %s)", instance.id, instance.source_plugin, target)
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [{"name": "sql", "type": "textarea", "required": True, "description": "SQL query to execute"}]

    def validate_params(self, params: dict[str, Any]) -> None:
        if not params.get("sql"):
            msg = "SQL query is required"
            raise ValueError(msg)

    def seed_defaults_for_source(self, source_name: str) -> None:
        from shenas_sources.core.transform import load_transform_defaults

        defaults = load_transform_defaults(source_name)
        if not defaults:
            return

        seed_rows = [
            {
                "source_duckdb_schema": d["source_duckdb_schema"],
                "source_duckdb_table": d["source_duckdb_table"],
                "target_duckdb_schema": d["target_duckdb_schema"],
                "target_duckdb_table": d["target_duckdb_table"],
                "description": d.get("description", ""),
                "params": json.dumps({"sql": d["sql"]}),
            }
            for d in defaults
        ]

        TransformInstance.seed_defaults(source_name, "sql", seed_rows)


__all__ = ["SqlTransformation"]
