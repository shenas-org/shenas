"""Statistical sanity checks for recipe results.

Plain rules-of-thumb refusing to claim findings when the data clearly
isn't there: too few rows, all-null inputs, zero variance, nonsense
correlation. The check produces a list of warning strings that the
runner attaches to the Result so the LLM iteration loop / the user
can see them. The result is NOT downgraded to an Error -- the user
still gets the number, just with a "this is not load-bearing" tag.

Each rule is a small function over a Result. Add new rules by appending
to ``SANITY_RULES``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shenas_analyses.core.analytics.runner import _ResultBase

_MIN_ROWS_FOR_CORRELATION = 10
_MIN_ROWS_FOR_TREND = 5


def _is_numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_scalar(result: _ResultBase) -> list[str]:
    warnings: list[str] = []
    value = getattr(result, "value", None)
    column = getattr(result, "column", "")
    if value is None:
        warnings.append("scalar result is null")
        return warnings
    if _is_numeric(value):
        if isinstance(value, float):
            if math.isnan(value):
                warnings.append("scalar result is NaN")
            elif math.isinf(value):
                warnings.append("scalar result is infinite")
        # Correlation-shaped column with implausible magnitude
        if "corr" in column.lower() and _is_numeric(value) and (value > 1.0 + 1e-9 or value < -1.0 - 1e-9):
            warnings.append(f"correlation {value:.3f} is outside [-1, 1]")
    return warnings


def _check_table(result: _ResultBase) -> list[str]:
    warnings: list[str] = []
    rows = list(getattr(result, "rows", []) or [])
    columns = list(getattr(result, "columns", []) or [])
    row_count = int(getattr(result, "row_count", len(rows)))

    if row_count == 0:
        warnings.append("table result is empty")
        return warnings
    if row_count < _MIN_ROWS_FOR_TREND:
        warnings.append(f"only {row_count} row(s); too few to establish a trend")

    # All-null detection per column.
    for col in columns:
        values = [r.get(col) for r in rows]
        if all(v is None for v in values):
            warnings.append(f"column `{col}` is all-null")
            continue
        numeric = [v for v in values if _is_numeric(v)]
        if len(numeric) >= _MIN_ROWS_FOR_CORRELATION and len(set(numeric)) == 1:
            warnings.append(f"column `{col}` has zero variance")

    return warnings


SANITY_RULES = {
    "scalar": _check_scalar,
    "table": _check_table,
}


def sanity_check(result: _ResultBase) -> list[str]:
    """Return human-readable sanity warnings for one Result.

    The list is empty when nothing trips. Caller is free to surface
    warnings in the UI without rejecting the result.
    """
    rule = SANITY_RULES.get(getattr(result, "type", ""))
    if rule is None:
        return []
    try:
        return rule(result)
    except Exception as exc:
        return [f"sanity check raised: {exc}"]
