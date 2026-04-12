"""Dataset plugin ABC."""

from __future__ import annotations

import json
import logging
from typing import Any, ClassVar

from shenas_plugins.core.plugin import Plugin, PluginInstance

log = logging.getLogger(f"shenas.{__name__}")

_GRAIN_TO_KIND: dict[str, str] = {
    "daily": "daily_metric",
    "weekly": "weekly_metric",
    "monthly": "monthly_metric",
    "event": "event_metric",
}

_GRAIN_TO_TIME_AT: dict[str, str] = {
    "daily": "date",
    "weekly": "week",
    "monthly": "month",
    "event": "occurred_at",
}


class Dataset(Plugin):
    """Canonical metrics schema."""

    _kind = "dataset"
    has_data = True
    all_tables: ClassVar[list[type]]
    primary_table: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "all_tables"):
            cls.tables = [t._Meta.name for t in cls.all_tables]  # ty: ignore[unresolved-attribute]

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info["primary_table"] = self.primary_table
        return info

    @classmethod
    def ensure(cls, con: Any) -> None:
        from shenas_plugins.core.table import Table

        Table.ensure_schema(con, all_tables=cls.all_tables)  # ty: ignore[invalid-argument-type]

    @classmethod
    def ensure_all(cls, con: Any) -> None:
        """Ensure all installed dataset plugins have their tables created."""
        for dataset_cls in cls.load_all(include_internal=False):
            dataset_cls.ensure(con)

    @classmethod
    def metadata(cls) -> list[dict[str, Any]]:
        return [t.table_metadata() for t in cls.all_tables]  # ty: ignore[unresolved-attribute]

    # ------------------------------------------------------------------
    # Suggestion lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def accept_suggestion(name: str) -> dict[str, Any]:
        """Accept a suggested dataset: create the metric table + transforms.

        1. Look up the PluginInstance with ``is_suggested=True``.
        2. Generate and execute DDL from ``metadata_json``.
        3. Create Transform rows for the bundled transforms.
        4. Flip ``is_suggested`` to False.
        """
        from shenas_transformers.core.transform import Transform

        from app.database import cursor

        pi = PluginInstance.find("dataset", name)
        if pi is None or not pi.is_suggested:
            msg = f"No suggested dataset named '{name}'"
            raise ValueError(msg)

        meta = pi.metadata
        columns = meta.get("columns", [])
        primary_key = meta.get("primary_key", [])
        table_name = meta.get("table_name", name)

        # Build DDL
        ddl = _build_ddl(table_name, columns, primary_key)
        with cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS metrics")
            cur.execute(ddl)

        # Create transform instances
        created_transforms: list[int] = []
        for t in meta.get("transforms", []):
            ti = Transform.create(
                transform_type="sql",
                source_data_resource_id=f"{t['source_schema']}.{t['source_table']}",
                target_data_resource_id=f"metrics.{table_name}",
                source_plugin=t["source_plugin"],
                params=json.dumps({"sql": t["sql"]}),
                description=t.get("description", ""),
            )
            created_transforms.append(ti.id)

        # Run the new transforms
        from app.database import connect

        con = connect()
        for tid in created_transforms:
            ti = Transform.find(tid)
            if ti and ti.enabled:
                try:
                    Transform.run_for_target(con, table_name)
                except Exception:
                    log.exception("Failed to run transforms for %s", table_name)
                break

        # Accept
        pi.is_suggested = False
        pi.save()

        return {
            "name": name,
            "table": f"metrics.{table_name}",
            "transforms_created": created_transforms,
        }

    @staticmethod
    def dismiss_suggestion(name: str) -> None:
        """Dismiss a suggested dataset: delete its PluginInstance row."""
        pi = PluginInstance.find("dataset", name)
        if pi is None or not pi.is_suggested:
            msg = f"No suggested dataset named '{name}'"
            raise ValueError(msg)
        pi.delete()

    @staticmethod
    def suggested_metadata(pi: PluginInstance) -> list[dict[str, Any]]:
        """Synthesize table_metadata dicts from a data-defined PluginInstance.

        Returns the same shape as ``Table.table_metadata()`` so the catalog
        walker can include data-defined datasets alongside code-based ones.
        """
        meta = pi.metadata
        if not meta:
            return []
        table_name = meta.get("table_name", pi.name)
        grain = meta.get("grain", "daily")
        kind = _GRAIN_TO_KIND.get(grain, "daily_metric")
        time_at = _GRAIN_TO_TIME_AT.get(grain, "date")
        columns = []
        for c in meta.get("columns", []):
            col: dict[str, Any] = {
                "name": c["name"],
                "db_type": c.get("db_type", "VARCHAR"),
                "nullable": c.get("nullable", True),
            }
            if c.get("description"):
                col["description"] = c["description"]
            if c.get("unit"):
                col["unit"] = c["unit"]
            columns.append(col)
        return [
            {
                "table": table_name,
                "schema": "metrics",
                "description": meta.get("description", ""),
                "primary_key": meta.get("primary_key", []),
                "columns": columns,
                "kind": kind,
                "time_columns": {"time_at": time_at},
                "query_hint": f"Data-defined metric table ({grain} grain).",
            }
        ]


def _build_ddl(table_name: str, columns: list[dict[str, Any]], primary_key: list[str]) -> str:
    """Generate CREATE TABLE DDL from JSON column definitions."""
    lines: list[str] = []
    for c in columns:
        db_type = c.get("db_type", "VARCHAR")
        not_null = " NOT NULL" if c["name"] in primary_key else ""
        lines.append(f'    "{c["name"]}" {db_type}{not_null}')
    lines.append(f"    PRIMARY KEY ({', '.join(f'{pk!r}' for pk in primary_key)})")
    return f'CREATE TABLE IF NOT EXISTS "metrics"."{table_name}" (\n' + ",\n".join(lines) + "\n)"
