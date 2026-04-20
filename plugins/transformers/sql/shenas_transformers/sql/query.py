"""Structured SELECT query builder backed by dataclasses.

Non-technical users build queries via the UI by picking columns,
adding filters, etc. The frontend sends structured objects; this
module generates parameterized SQL on the backend.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from typing import Any

# Only allow safe identifier characters (letters, digits, underscore).
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

VALID_AGGREGATES = frozenset({"sum", "avg", "count", "min", "max"})
VALID_OPERATORS = frozenset(
    {
        "eq",
        "neq",
        "gt",
        "lt",
        "gte",
        "lte",
        "contains",
        "starts_with",
        "is_null",
        "is_not_null",
    }
)
VALID_DIRECTIONS = frozenset({"asc", "desc"})

_OPERATOR_SQL: dict[str, str] = {
    "eq": "= ?",
    "neq": "!= ?",
    "gt": "> ?",
    "lt": "< ?",
    "gte": ">= ?",
    "lte": "<= ?",
    "contains": "LIKE ?",
    "starts_with": "LIKE ?",
    "is_null": "IS NULL",
    "is_not_null": "IS NOT NULL",
}


def _validate_identifier(name: str) -> str:
    if not _IDENT_RE.match(name):
        msg = f"Invalid identifier: {name!r}"
        raise ValueError(msg)
    return name


@dataclass
class SelectColumn:
    name: str
    alias: str | None = None
    aggregate: str | None = None  # sum, avg, count, min, max

    def to_sql(self) -> str:
        col = _validate_identifier(self.name)
        if self.aggregate:
            if self.aggregate not in VALID_AGGREGATES:
                msg = f"Invalid aggregate: {self.aggregate!r}"
                raise ValueError(msg)
            expr = f"{self.aggregate.upper()}({col})"
            alias = self.alias or f"{self.name}_{self.aggregate}"
        else:
            expr = col
            alias = self.alias

        if alias:
            _validate_identifier(alias)
            return f"{expr} AS {alias}"
        return expr


@dataclass
class Filter:
    column: str
    operator: str  # eq, neq, gt, lt, gte, lte, contains, starts_with, is_null, is_not_null
    value: str | None = None

    def to_sql(self) -> tuple[str, list[Any]]:
        """Return (SQL fragment, bind params)."""
        col = _validate_identifier(self.column)
        if self.operator not in VALID_OPERATORS:
            msg = f"Invalid operator: {self.operator!r}"
            raise ValueError(msg)

        sql_op = _OPERATOR_SQL[self.operator]
        if self.operator in ("is_null", "is_not_null"):
            return f"{col} {sql_op}", []
        if self.operator == "contains":
            return f"{col} {sql_op}", [f"%{self.value}%"]
        if self.operator == "starts_with":
            return f"{col} {sql_op}", [f"{self.value}%"]
        return f"{col} {sql_op}", [self.value]


@dataclass
class OrderBy:
    column: str
    direction: str = "asc"

    def to_sql(self) -> str:
        col = _validate_identifier(self.column)
        if self.direction not in VALID_DIRECTIONS:
            msg = f"Invalid direction: {self.direction!r}"
            raise ValueError(msg)
        return f"{col} {self.direction.upper()}"


@dataclass
class SelectQuery:
    """Structured representation of a SELECT query.

    Built by the frontend's SQL builder UI. The backend generates
    parameterized SQL from this structure.
    """

    columns: list[SelectColumn]
    filters: list[Filter] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    order_by: list[OrderBy] = field(default_factory=list)
    limit: int | None = None

    def to_sql(self, source: str) -> tuple[str, list[Any]]:
        """Generate a parameterized SELECT statement.

        Returns ``(sql_string, bind_params)``.
        """
        if not self.columns:
            msg = "SelectQuery requires at least one column"
            raise ValueError(msg)

        col_exprs = [col.to_sql() for col in self.columns]
        parts = [f"SELECT {', '.join(col_exprs)}", f"FROM {source}"]

        bind_params: list[Any] = []
        if self.filters:
            where_clauses = []
            for filt in self.filters:
                clause, params = filt.to_sql()
                where_clauses.append(clause)
                bind_params.extend(params)
            parts.append(f"WHERE {' AND '.join(where_clauses)}")

        if self.group_by:
            group_cols = [_validate_identifier(col) for col in self.group_by]
            parts.append(f"GROUP BY {', '.join(group_cols)}")

        if self.order_by:
            order_exprs = [ob.to_sql() for ob in self.order_by]
            parts.append(f"ORDER BY {', '.join(order_exprs)}")

        if self.limit is not None:
            parts.append(f"LIMIT {int(self.limit)}")

        return "\n".join(parts), bind_params

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SelectQuery:
        """Reconstruct from a dict (e.g. parsed JSON params)."""
        columns = [SelectColumn(**col) for col in data.get("columns", [])]
        filters = [Filter(**filt) for filt in data.get("filters", [])]
        order_by = [OrderBy(**ob) for ob in data.get("order_by", [])]
        group_by = data.get("group_by", [])
        limit = data.get("limit")
        return cls(
            columns=columns,
            filters=filters,
            group_by=group_by,
            order_by=order_by,
            limit=int(limit) if limit is not None else None,
        )
