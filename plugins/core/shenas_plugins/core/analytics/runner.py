"""Recipe runner: compile + execute + result-shape.

This is the layer between :class:`Recipe.compile` (which returns an
:class:`ibis.Expr`) and a caller that wants typed, JSON-serializable
results back. It runs the compiled expression against an Ibis backend
and shapes the output into a tagged-union :class:`Result` so consumers
(the future hypothesis record, the future GraphQL endpoint, the future
LLM interpretation step) can pattern-match on what came back.

Three result shapes:

- :class:`ScalarResult` -- one row, one column. Most correlate /
  aggregate recipes land here.
- :class:`TableResult` -- many rows or many columns. Resample / lag
  / join_as_of recipes typically land here. Capped at
  ``max_rows`` (default 10_000); larger results are truncated and
  flagged ``truncated=True`` so callers don't accidentally render
  millions of rows.
- :class:`ErrorResult` -- something went wrong. ``kind`` distinguishes
  validation / operation / execution / timeout failures so the LLM
  iteration loop can decide whether to retry or surface to the user.

The runner does NOT enforce a hard SQL-level read-only constraint. The
analytics layer (``operations.py`` + ``recipe.py``) only emits SELECT
expressions, so writes are impossible *by construction*. A future
hardening pass can spawn a separate read-only DuckDB connection if the
soft guarantee turns out not to be enough.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from shenas_plugins.core.analytics.operations import OperationError
from shenas_plugins.core.analytics.recipe import Recipe, RecipeError

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Result tagged union
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class ScalarResult:
    """A single value (one-row, one-column result).

    Returned for recipes whose final node is a scalar aggregation
    (correlate, an aggregate.count, etc).
    """

    value: float | int | str | bool | None
    column: str
    elapsed_ms: float = 0.0
    sql: str = ""

    type: str = "scalar"  # for JSON serialization


@dataclass(frozen=True)
class TableResult:
    """A multi-row result.

    Returned for recipes whose final node is anything other than a
    one-row aggregation. Truncates at ``max_rows`` (default 10_000);
    callers can check ``truncated`` to know whether to warn the user.
    """

    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    elapsed_ms: float = 0.0
    sql: str = ""

    type: str = "table"  # for JSON serialization


@dataclass(frozen=True)
class ErrorResult:
    """Something went wrong during compilation or execution.

    ``kind`` lets the LLM iteration loop distinguish failures it might
    retry from failures it should surface immediately:

    - ``"validation"`` -- recipe is structurally invalid (RecipeError).
      LLM should re-plan with the error message.
    - ``"operation"`` -- an operation rejected its inputs (OperationError).
      LLM should re-plan; the column / kind is wrong.
    - ``"execution"`` -- the SQL ran but DuckDB raised an error
      (type mismatch, division by zero, ...). May be a real bug or a
      bad recipe; surface to the user.
    - ``"timeout"`` -- exceeded ``timeout_seconds``. Surface to user.
    """

    message: str
    kind: str  # "validation" | "operation" | "execution" | "timeout"
    elapsed_ms: float = 0.0
    sql: str = ""

    type: str = "error"  # for JSON serialization


Result = ScalarResult | TableResult | ErrorResult


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------


def run_recipe(
    recipe: Recipe,
    catalog: dict[str, dict[str, Any]],
    *,
    backend: Any | None = None,
    timeout_seconds: float = 30.0,
    max_rows: int = 10_000,
) -> Result:
    """Compile and execute a recipe, returning a tagged-union ``Result``.

    Parameters
    ----------
    recipe
        The :class:`Recipe` to run.
    catalog
        ``{qualified_table: table_metadata}`` -- as produced by walking
        :meth:`Table.table_metadata` over all source / metric tables in
        the schema. The compiler uses ``kind`` and ``time_columns`` to
        validate operations.
    backend
        An Ibis Backend (typically from :func:`app.db.analytics_backend`).
        Tests inject an in-memory backend; production callers leave it
        ``None`` to get the encrypted-DB-backed one.
    timeout_seconds
        Soft wall-clock budget. The query is run on a worker thread; if
        the thread doesn't finish in ``timeout_seconds`` we return an
        ``ErrorResult(kind="timeout")``. **The underlying DuckDB query
        keeps running in the background** -- a real cancellation
        requires DuckDB ``con.interrupt()`` and is deferred to Phase 4.
    max_rows
        Truncate ``TableResult.rows`` at this many. The full row count
        is still reported via ``row_count``; ``truncated=True`` flags it.

    Returns
    -------
    Result
        Always returns a Result; never raises (errors are wrapped in
        :class:`ErrorResult`). This makes the LLM iteration loop's job
        easier -- it never has to handle exceptions, just check the
        result type.
    """
    started = time.perf_counter()
    sql = ""

    if backend is None:
        from app.db import analytics_backend

        backend = analytics_backend()

    # 1) Compile (structural validation + topo walk + ibis lowering).
    try:
        result_node = recipe.compile(backend, catalog)
    except RecipeError as exc:
        return ErrorResult(
            message=str(exc),
            kind="validation",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    except OperationError as exc:
        return ErrorResult(
            message=str(exc),
            kind="operation",
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )

    # 2) Render the SQL (for "show your work" -- attached to all result kinds).
    try:
        import ibis

        sql = str(ibis.to_sql(result_node.expr, dialect="duckdb"))
    except Exception:
        # SQL rendering shouldn't fail post-compile, but if it does,
        # don't let it block execution -- just leave sql empty.
        sql = ""

    # 3) Execute on a worker thread with a soft wall-clock timeout.
    container: dict[str, Any] = {}

    def _exec() -> None:
        try:
            container["df"] = result_node.expr.execute()
        except Exception as exc:
            container["exc"] = exc

    worker = threading.Thread(target=_exec, daemon=True)
    worker.start()
    worker.join(timeout=timeout_seconds)

    elapsed_ms = (time.perf_counter() - started) * 1000

    if worker.is_alive():
        # Soft timeout: caller is unblocked but DuckDB keeps running until
        # it finishes its query. A future hardening pass can call
        # con.interrupt() to actually cancel.
        logger.warning("recipe execution exceeded %ss timeout", timeout_seconds)
        return ErrorResult(
            message=f"execution exceeded {timeout_seconds}s timeout",
            kind="timeout",
            elapsed_ms=elapsed_ms,
            sql=sql,
        )

    if "exc" in container:
        return ErrorResult(
            message=f"{type(container['exc']).__name__}: {container['exc']}",
            kind="execution",
            elapsed_ms=elapsed_ms,
            sql=sql,
        )

    df = container["df"]

    # 4) Shape into ScalarResult vs TableResult.
    if df.shape == (1, 1):
        col = df.columns[0]
        raw = df.iloc[0, 0]
        # Convert numpy / pandas scalars to native Python for JSON.
        value = _coerce_scalar(raw)
        return ScalarResult(value=value, column=str(col), elapsed_ms=elapsed_ms, sql=sql)

    full_count = len(df)
    truncated = full_count > max_rows
    if truncated:
        df = df.head(max_rows)
    rows = df.to_dict("records")
    # Coerce each cell value for JSON serialization.
    rows = [{k: _coerce_scalar(v) for k, v in row.items()} for row in rows]
    return TableResult(
        rows=rows,
        columns=[str(c) for c in df.columns],
        row_count=full_count,
        truncated=truncated,
        elapsed_ms=elapsed_ms,
        sql=sql,
    )


def _coerce_scalar(value: Any) -> Any:
    """Convert numpy / pandas scalars to native Python types for JSON.

    Returns ``None`` for NaN / NA / NaT. Pass strings, ints, floats,
    bools through unchanged. Falls back to ``str()`` for anything
    exotic so the JSON serializer never blows up.
    """
    if value is None:
        return None
    # numpy / pandas have their own NaN / NaT sentinels
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
    except Exception:
        pass
    # numpy types: have a .item() method that returns the python value
    import contextlib

    item = getattr(value, "item", None)
    if callable(item):
        with contextlib.suppress(Exception):
            value = item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    # pandas Timestamp / Timedelta and others -> isoformat / str
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            pass
    return str(value)
