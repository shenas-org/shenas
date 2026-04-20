"""SQL transformer plugin -- executes SQL transforms (raw or structured)."""

from __future__ import annotations

import contextlib
import json
from typing import Any

import duckdb
from shenas_transformers.core import TableTransformer
from shenas_transformers.core.transform import Transform


def _resolve_sql(params: dict[str, Any], source: str) -> tuple[str, list[Any]]:
    """Extract SQL from params -- structured SelectQuery or raw string."""
    if "columns" in params:
        from shenas_transformers.sql.query import SelectQuery

        query = SelectQuery.from_dict(params)
        return query.to_sql(source)
    sql = params.get("sql", "")
    return sql, []


class SqlTransformer(TableTransformer):
    """Execute SQL to transform source data into target tables.

    Supports two modes:
    - **Builder**: structured SelectQuery (columns, filters, order_by, etc.)
    - **Raw**: arbitrary SQL string for power users
    """

    name = "sql"
    display_name = "SQL Transformer"
    description = "Transform source data using SQL -- use the builder for simple queries or raw SQL for complex ones."
    internal = True

    def execute(
        self,
        transform: Transform,
        *,
        device_id: str = "local",
    ) -> int:
        params = transform.get_params()
        source_qualified = f'"{transform.source_ref.schema}"."{transform.source_ref.table}"'
        sql, bind_params = _resolve_sql(params, source_qualified)
        if not sql:
            self.log.warning("Transform #%d has no SQL in params", transform.id)
            return 0

        target = f'"{transform.target_ref.schema}"."{transform.target_ref.table}"'
        try:
            from app.database import cursor

            with cursor() as cur:
                # Skip if the source table doesn't exist yet
                source_ref = transform.source_ref
                row = cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
                    [source_ref.schema, source_ref.table],
                ).fetchone()
                if not row:
                    self.log.debug(
                        "Transform #%d skipped: source table %s.%s does not exist",
                        transform.id,
                        source_ref.schema,
                        source_ref.table,
                    )
                    return 0

                cur.execute(f"DELETE FROM {target} WHERE source = ?", [transform.source_plugin])

                # Validate and infer columns
                if bind_params:
                    cur.execute(f"SELECT * FROM ({sql}) _t LIMIT 0", bind_params)
                else:
                    cur.execute(f"SELECT * FROM ({sql}) _t LIMIT 0")
                cols = [d[0] for d in cur.description]

                col_names = ", ".join(f'"{c}"' for c in cols)

                with contextlib.suppress(duckdb.Error):
                    cur.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

                col_names_with_device = col_names + ', "source_device"'
                wrapped_sql = f"SELECT *, '{device_id}' as source_device FROM ({sql}) _t"
                if bind_params:
                    cur.execute(f"INSERT INTO {target} ({col_names_with_device}) {wrapped_sql}", bind_params)
                else:
                    cur.execute(f"INSERT INTO {target} ({col_names_with_device}) {wrapped_sql}")
            return 1
        except Exception:
            self.log.exception("Transform #%d failed (%s -> %s)", transform.id, transform.source_plugin, target)
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "mode",
                "label": "Mode",
                "type": "select",
                "required": False,
                "description": "Builder for simple queries, raw SQL for complex ones",
                "default": "builder",
                "options": ["builder", "raw"],
            },
            {
                "name": "sql",
                "label": "SQL query",
                "type": "textarea",
                "required": False,
                "description": "SQL query to execute",
                "visible_when": {"mode": "raw"},
            },
        ]

    def validate_params(self, params: dict[str, Any]) -> None:
        mode = params.get("mode", "builder")
        if mode == "raw" and not params.get("sql"):
            msg = "SQL query is required in raw mode"
            raise ValueError(msg)
        if mode == "builder" and not params.get("columns"):
            msg = "At least one column is required in builder mode"
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
                "params": json.dumps({"sql": d["sql"], "mode": "raw"}),
            }
            for d in defaults
        ]

        Transform.seed_defaults(source_name, "sql", seed_rows)


__all__ = ["SqlTransformer"]
