"""SQL transformer plugin -- executes arbitrary SQL transforms."""

from __future__ import annotations

import contextlib
import json
from typing import Any

import duckdb
from shenas_transformers.core import TableTransformer
from shenas_transformers.core.transform import Transform


class SqlTransformer(TableTransformer):
    """Execute arbitrary SQL to transform source data into target tables."""

    name = "sql"
    display_name = "SQL Transformer"
    description = "Execute arbitrary SQL to transform source data into target tables."
    internal = True

    def execute(
        self,
        transform: Transform,
        *,
        device_id: str = "local",
    ) -> int:
        params = transform.get_params()
        sql = params.get("sql", "")
        if not sql:
            self.log.warning("Transform #%d has no SQL in params", transform.id)
            return 0

        target = f'"{transform.target_ref.schema}"."{transform.target_ref.table}"'
        try:
            from app.database import cursor

            with cursor() as cur:
                # Skip if the source table doesn't exist yet (e.g. first sync returned no data).
                src = transform.source_ref
                row = cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
                    [src.schema, src.table],
                ).fetchone()
                if not row:
                    self.log.debug(
                        "Transform #%d skipped: source table %s.%s does not exist",
                        transform.id,
                        src.schema,
                        src.table,
                    )
                    return 0

                cur.execute(f"DELETE FROM {target} WHERE source = ?", [transform.source_plugin])
                cur.execute(f"SELECT * FROM ({sql}) _t LIMIT 0")
                cols = [d[0] for d in cur.description]

                col_names = ", ".join(f'"{c}"' for c in cols)

                with contextlib.suppress(duckdb.Error):
                    cur.execute(f"ALTER TABLE {target} ADD COLUMN source_device TEXT DEFAULT 'local'")

                col_names_with_device = col_names + ', "source_device"'
                sql_with_device = f"SELECT *, '{device_id}' as source_device FROM ({sql}) _t"
                cur.execute(f"INSERT INTO {target} ({col_names_with_device}) {sql_with_device}")
            return 1
        except Exception:
            self.log.exception("Transform #%d failed (%s -> %s)", transform.id, transform.source_plugin, target)
            return 0

    def param_schema(self) -> list[dict[str, Any]]:
        return [
            {"name": "sql", "label": "SQL query", "type": "textarea", "required": True, "description": "SQL query to execute"}
        ]

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

        Transform.seed_defaults(source_name, "sql", seed_rows)


__all__ = ["SqlTransform"]
