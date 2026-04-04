"""Generic single-row dataclass table storage in DuckDB.

Used by both config and auth modules. Each gets its own DuckDB schema
but shares the same CRUD logic.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from app.db import cursor

from shenas_schemas.core.ddl import generate_ddl
from shenas_schemas.core.introspect import table_metadata


class DataclassStore:
    """Single-row dataclass-backed table store in a named DuckDB schema."""

    def __init__(self, schema: str) -> None:
        self.schema = schema
        self._ensured: set[str] = set()

    def ensure_table(self, cls: type) -> None:
        table = cls.__table__
        if table in self._ensured:
            return

        with cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            ddl = generate_ddl(cls).replace("metrics.", f"{self.schema}.")
            cur.execute(ddl)

            existing = {
                r[0]
                for r in cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
                    [self.schema, table],
                ).fetchall()
            }
            meta = table_metadata(cls)
            for col in meta["columns"]:
                if col["name"] not in existing:
                    db_type = col.get("db_type", "VARCHAR")
                    cur.execute(f"ALTER TABLE {self.schema}.{table} ADD COLUMN {col['name']} {db_type}")

        self._ensured.add(table)

    def get(self, cls: type) -> dict[str, Any] | None:
        self.ensure_table(cls)
        table = cls.__table__
        cols = [f.name for f in dataclasses.fields(cls)]
        col_list = ", ".join(cols)
        with cursor() as cur:
            row = cur.execute(f"SELECT {col_list} FROM {self.schema}.{table} LIMIT 1").fetchone()
        if row is None:
            return None
        return dict(zip(cols, row))

    def get_value(self, cls: type, key: str) -> Any | None:
        row = self.get(cls)
        if row is None:
            return None
        return row.get(key)

    def set(self, cls: type, **kwargs: Any) -> None:
        self.ensure_table(cls)
        table = cls.__table__

        existing = self.get(cls)
        if existing:
            merged = {**existing, **kwargs}
        else:
            defaults = {}
            for f in dataclasses.fields(cls):
                if f.default is not dataclasses.MISSING:
                    defaults[f.name] = f.default
                elif f.default_factory is not dataclasses.MISSING:
                    defaults[f.name] = f.default_factory()
                else:
                    defaults[f.name] = None
            merged = {**defaults, **kwargs}

        cols = [f.name for f in dataclasses.fields(cls)]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        values = [merged.get(c) for c in cols]
        with cursor() as cur:
            cur.execute(f"DELETE FROM {self.schema}.{table}")
            cur.execute(f"INSERT INTO {self.schema}.{table} ({col_names}) VALUES ({placeholders})", values)

    def delete(self, cls: type) -> None:
        self.ensure_table(cls)
        table = cls.__table__
        with cursor() as cur:
            cur.execute(f"DELETE FROM {self.schema}.{table}")

    def metadata(self, cls: type) -> dict[str, Any]:
        return table_metadata(cls)
