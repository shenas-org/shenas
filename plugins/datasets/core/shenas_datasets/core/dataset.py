"""Dataset plugin ABC."""

from __future__ import annotations

import json
import logging
from typing import Any, ClassVar

from app.plugin import Plugin, PluginInstance

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
    # Entity types this dataset is *about*. When the list contains a single
    # type like ``["human"]`` without a specific entity being set, the data
    # is implicitly about the current user ("me").
    entity_types: ClassVar[list[str]] = []
    # ISO 8601 recurring interval describing how often this dataset refreshes
    # once its feeding transforms have run (e.g. "R/P1D" for daily rollups).
    # Mirrors DCAT's `dct:accrualPeriodicity`. Empty string means unspecified.
    default_update_frequency: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "all_tables"):
            # Prefix table names with the dataset plugin name so all dataset
            # data lives in one schema:
            #   metrics.daily_habits -> datasets.habits__daily_habits
            from app.schema import DATASETS

            for t in cls.all_tables:
                overrides: dict[str, object] = {}
                if not getattr(t._Meta, "schema", None) or t._Meta.schema != DATASETS:  # ty: ignore[unresolved-attribute]
                    overrides["schema"] = DATASETS
                name = t._Meta.name  # ty: ignore[unresolved-attribute]
                prefixed = f"{cls.name}__{name}"
                if not name.startswith(f"{cls.name}__"):
                    overrides["name"] = prefixed
                if overrides:
                    t._Meta = type("_Meta", (t._Meta,), overrides)  # ty: ignore[unresolved-attribute]
            cls.tables = [t._Meta.name for t in cls.all_tables]  # ty: ignore[unresolved-attribute]

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info["primary_table"] = self.primary_table
        info["default_update_frequency"] = self.default_update_frequency
        info["entity_types"] = list(self.entity_types)
        info["entity_uuids"] = self.resolve_entity_uuids(self.entity_types)
        info["tables"] = list(getattr(self, "tables", []))
        info["table_metadata"] = self._table_metadata()
        return info

    def _table_metadata(self) -> list[dict[str, Any]]:
        """Return table metadata with live stats for all dataset tables."""
        result: list[dict[str, Any]] = []
        for table_cls in getattr(self, "all_tables", []):
            try:
                meta = table_cls.metadata()
                if hasattr(meta.get("schema"), "name"):
                    meta["schema"] = meta["schema"].name
                meta.update(self._live_table_stats(meta.get("schema", "datasets"), meta["table"]))
                result.append(meta)
            except Exception:
                continue
        return result

    @staticmethod
    def _live_table_stats(schema: str, table: str) -> dict[str, Any]:
        """Query DuckDB for row count and date range of a table."""
        try:
            from app.database import cursor

            qualified = f'"{schema}"."{table}"'
            with cursor() as cur:
                row = cur.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
                rows = row[0] if row else 0
                earliest = None
                latest = None
                for date_col in ("date", "calendar_date", "start_time_local", "occurred_at", "month"):
                    try:
                        result = cur.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {qualified}").fetchone()
                        if result and result[0]:
                            earliest = str(result[0])[:10]
                            latest = str(result[1])[:10]
                            break
                    except Exception:
                        continue
                return {"rows": rows, "earliest": earliest, "latest": latest}
        except Exception:
            return {"rows": 0, "earliest": None, "latest": None}

    @classmethod
    def ensure(cls) -> None:
        from app.table import Table

        Table.ensure_schema(all_tables=cls.all_tables)  # ty: ignore[invalid-argument-type]

    @classmethod
    def ensure_all(cls) -> None:
        """Ensure all installed dataset plugins have their tables created."""
        for dataset_cls in cls.load_all(include_internal=False):
            dataset_cls.ensure()

    @classmethod
    def metadata(cls) -> list[dict[str, Any]]:
        return [t.metadata() for t in cls.all_tables]  # ty: ignore[unresolved-attribute]

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
            from app.schema import DATASETS

            DATASETS.ensure()
            cur.execute(ddl)

        # Create transform instances
        created_transforms: list[int] = []
        for t in meta.get("transforms", []):
            ti = Transform.create(
                transform_type="sql",
                source_data_resource_id=f"{t['source_schema']}.{t['source_table']}",
                target_data_resource_id=f"datasets.{table_name}",
                source_plugin=t["source_plugin"],
                params=json.dumps({"sql": t["sql"]}),
                description=t.get("description", ""),
            )
            created_transforms.append(ti.id)

        # Run the new transforms

        for tid in created_transforms:
            ti = Transform.find(tid)
            if ti and ti.enabled:
                try:
                    Transform.run_for_target(table_name)
                except Exception:
                    log.exception("Failed to run transforms for %s", table_name)
                break

        # Accept
        pi.is_suggested = False
        pi.save()

        return {
            "name": name,
            "table": f"datasets.{table_name}",
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

        Returns the same shape as ``Table.metadata()`` so the catalog
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
                "schema": "datasets",
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
    pk_cols = ", ".join(f'"{pk}"' for pk in primary_key)
    lines.append(f"    PRIMARY KEY ({pk_cols})")
    return f'CREATE TABLE IF NOT EXISTS "datasets"."{table_name}" (\n' + ",\n".join(lines) + "\n)"
