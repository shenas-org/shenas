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
VALID_GRAINS = frozenset({"day", "week", "month", "year", "hour"})
VALID_RESAMPLE_FUNCS = frozenset({"avg", "sum", "min", "max", "count", "first", "last"})

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
class LagConfig:
    """Add LAG window columns to the output."""

    column: str
    periods: int = 1
    order_by: str | None = None  # defaults to time_at if available

    def to_sql(self, time_col: str | None = None) -> str:
        col = _validate_identifier(self.column)
        order_col = _validate_identifier(self.order_by or time_col or col)
        alias = f"{self.column}_lag{self.periods}"
        _validate_identifier(alias)
        return f"LAG({col}, {int(self.periods)}) OVER (ORDER BY {order_col}) AS {alias}"


@dataclass
class ResampleConfig:
    """Resample time-series to a coarser grain via DATE_TRUNC + GROUP BY."""

    grain: str  # day, week, month, year, hour
    time_column: str
    func: str = "avg"  # aggregation for non-grouped columns

    def validate(self) -> None:
        if self.grain not in VALID_GRAINS:
            msg = f"Invalid grain: {self.grain!r}"
            raise ValueError(msg)
        if self.func not in VALID_RESAMPLE_FUNCS:
            msg = f"Invalid resample function: {self.func!r}"
            raise ValueError(msg)
        _validate_identifier(self.time_column)


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
    lags: list[LagConfig] = field(default_factory=list)
    resample: ResampleConfig | None = None

    def to_sql(self, source: str) -> tuple[str, list[Any]]:
        """Generate a parameterized SELECT statement.

        Returns ``(sql_string, bind_params)``.
        """
        if not self.columns:
            msg = "SelectQuery requires at least one column"
            raise ValueError(msg)

        col_exprs = [col.to_sql() for col in self.columns]

        # Add lag window columns
        time_col = self.resample.time_column if self.resample else None
        col_exprs.extend(lag.to_sql(time_col) for lag in self.lags)

        # Resample: wrap columns with DATE_TRUNC for the time column
        # and aggregate non-time, non-group columns
        if self.resample:
            self.resample.validate()
            col_exprs = self._apply_resample(col_exprs)

        parts = [f"SELECT {', '.join(col_exprs)}", f"FROM {source}"]

        bind_params: list[Any] = []
        if self.filters:
            where_clauses = []
            for filt in self.filters:
                clause, params = filt.to_sql()
                where_clauses.append(clause)
                bind_params.extend(params)
            parts.append(f"WHERE {' AND '.join(where_clauses)}")

        if self.resample:
            # Auto-generate GROUP BY from resample
            group_cols = self._resample_group_cols()
            parts.append(f"GROUP BY {', '.join(group_cols)}")
        elif self.group_by:
            group_cols = [_validate_identifier(col) for col in self.group_by]
            parts.append(f"GROUP BY {', '.join(group_cols)}")

        if self.order_by:
            order_exprs = [ob.to_sql() for ob in self.order_by]
            parts.append(f"ORDER BY {', '.join(order_exprs)}")

        if self.limit is not None:
            parts.append(f"LIMIT {int(self.limit)}")

        return "\n".join(parts), bind_params

    def _apply_resample(self, col_exprs: list[str]) -> list[str]:
        """Replace time column with DATE_TRUNC, wrap others with aggregate."""
        resample = self.resample
        assert resample is not None
        time_col = _validate_identifier(resample.time_column)
        func = resample.func.upper()
        grain = resample.grain

        result = []
        group_col_names = set(self.group_by) | {resample.time_column}
        for expr in col_exprs:
            # Check if this is the time column (plain or aliased)
            col_name = expr.split(" AS ")[0].strip() if " AS " in expr else expr
            if col_name == time_col:
                result.append(f"DATE_TRUNC('{grain}', {time_col}) AS {time_col}")
            elif col_name in group_col_names:
                result.append(expr)
            elif "LAG(" in expr or "OVER" in expr:
                # Skip lag columns -- they don't aggregate
                continue
            else:
                # Wrap with aggregate function
                alias = expr.split(" AS ")[-1].strip() if " AS " in expr else col_name
                result.append(f"{func}({col_name}) AS {alias}")
        return result

    def _resample_group_cols(self) -> list[str]:
        """Build GROUP BY columns for resample."""
        resample = self.resample
        assert resample is not None
        time_col = _validate_identifier(resample.time_column)
        cols = [f"DATE_TRUNC('{resample.grain}', {time_col})"]
        cols.extend(_validate_identifier(col) for col in self.group_by)
        return cols

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
        lags = [LagConfig(**lag) for lag in data.get("lags", [])]
        resample_raw = data.get("resample")
        resample = ResampleConfig(**resample_raw) if resample_raw else None
        return cls(
            columns=columns,
            filters=filters,
            group_by=group_by,
            order_by=order_by,
            limit=int(limit) if limit is not None else None,
            lags=lags,
            resample=resample,
        )
