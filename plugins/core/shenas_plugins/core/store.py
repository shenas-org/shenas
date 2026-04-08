"""Generic single-row dataclass table storage in DuckDB.

Used by both config and auth modules. Each gets its own DuckDB schema
but shares the same CRUD logic.
"""

from __future__ import annotations

import dataclasses
from typing import Any, ClassVar

from shenas_plugins.core.introspect import table_metadata


class TableStore:
    """Single-row dataclass-backed table store in a named DuckDB schema."""

    _ensured_by_schema: ClassVar[dict[str, set[str]]] = {}

    def __init__(self, schema: str) -> None:
        self.schema = schema
        if schema not in self._ensured_by_schema:
            self._ensured_by_schema[schema] = set()

    @property
    def _ensured(self) -> set[str]:
        return self._ensured_by_schema[self.schema]

    @staticmethod
    def _cursor():
        from app.db import cursor

        return cursor()

    def ensure_table(self, cls: type) -> None:
        table = cls.table_name
        if table in self._ensured:
            return

        from shenas_plugins.core.ddl import ensure_schema

        with self._cursor() as cur:
            ensure_schema(cur, [cls], schema=self.schema)

        self._ensured.add(table)

    def get(self, cls: type) -> dict[str, Any] | None:
        self.ensure_table(cls)
        table = cls.table_name
        cols = [f.name for f in dataclasses.fields(cls)]
        col_list = ", ".join(cols)
        with self._cursor() as cur:
            row = cur.execute(f"SELECT {col_list} FROM {self.schema}.{table} LIMIT 1").fetchone()
        if row is None:
            return None
        return dict(zip(cols, row, strict=False))

    def get_value(self, cls: type, key: str) -> Any | None:
        row = self.get(cls)
        if row is None:
            return None
        return row.get(key)

    def set(self, cls: type, **kwargs: Any) -> None:
        self.ensure_table(cls)
        table = cls.table_name

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
        with self._cursor() as cur:
            cur.execute(f"DELETE FROM {self.schema}.{table}")
            cur.execute(f"INSERT INTO {self.schema}.{table} ({col_names}) VALUES ({placeholders})", values)

    def delete(self, cls: type) -> None:
        self.ensure_table(cls)
        table = cls.table_name
        with self._cursor() as cur:
            cur.execute(f"DELETE FROM {self.schema}.{table}")

    def metadata(self, cls: type) -> dict[str, Any]:
        return table_metadata(cls)
