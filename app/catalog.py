"""Lightweight catalog primitives shared by transforms, recipes, and the data catalog.

Kept separate from :mod:`app.data_catalog` (which is the runtime catalog
walker and its persistence tables) so these pure value types can be
imported without pulling in the walker and its plugin-discovery cost.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataResourceRef:
    """Lightweight typed reference to a DuckDB table.

    Used by transforms, recipes, catalog, and any other code that needs
    to reference a table without raw strings.
    """

    schema: str
    table: str

    @property
    def id(self) -> str:
        return f"{self.schema}.{self.table}"

    @classmethod
    def from_id(cls, data_resource_id: str) -> DataResourceRef:
        if not data_resource_id:
            msg = f"DataResourceRef.from_id: empty data_resource_id ({data_resource_id!r})"
            raise ValueError(msg)
        if "." not in data_resource_id:
            msg = f"DataResourceRef.from_id: expected 'schema.table', got {data_resource_id!r}"
            raise ValueError(msg)
        schema, table = data_resource_id.split(".", 1)
        return cls(schema=schema, table=table)

    def __str__(self) -> str:
        return self.id

    def quoted_sql(self) -> str:
        return f'"{self.schema}"."{self.table}"'
