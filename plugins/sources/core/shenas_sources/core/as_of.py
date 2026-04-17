"""AS-OF macro generator for SCD2 tables.

Every ``DimensionTable``, ``SnapshotTable``, and ``M2MTable`` is loaded by
dlt with the SCD2 strategy, which materialises ``_dlt_valid_from`` and
``_dlt_valid_to`` columns alongside the natural key. This module discovers
those tables in a given schema and creates a DuckDB macro per table:

::

    CREATE OR REPLACE MACRO <schema>.<table>_as_of(ts) AS TABLE
      SELECT * FROM <schema>.<table>
      WHERE _dlt_valid_from <= ts
        AND (_dlt_valid_to IS NULL OR _dlt_valid_to > ts);

Consumers can then write ``SELECT * FROM gcalendar.calendars_as_of('2026-01-15')``
to get the calendar names that were valid on that date instead of the
current ones.

Discovery is column-shape-based (any table with both ``_dlt_valid_from``
and ``_dlt_valid_to`` columns) so the macros are kept in sync with the
live tables on every run without per-source configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.plugin import Plugin

if TYPE_CHECKING:
    import duckdb

logger = Plugin.get_logger(__name__)


def find_scd2_tables(con: duckdb.DuckDBPyConnection, schema: str) -> list[str]:
    """Return the names of tables in `schema` that have SCD2 columns.

    A table is considered SCD2 if it has both ``_dlt_valid_from`` and
    ``_dlt_valid_to`` columns. dlt's SCD2 strategy adds these alongside
    the natural key on every dimension/snapshot/m2m table.
    """
    rows = con.execute(
        """
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = ?
          AND column_name IN ('_dlt_valid_from', '_dlt_valid_to')
        GROUP BY table_name
        HAVING COUNT(DISTINCT column_name) = 2
        ORDER BY table_name
        """,
        [schema],
    ).fetchall()
    return [r[0] for r in rows]


def _quote(ident: str) -> str:
    """Quote a SQL identifier, escaping any embedded double quotes."""
    return '"' + ident.replace('"', '""') + '"'


def apply_as_of_macros(con: duckdb.DuckDBPyConnection, schema: str) -> list[str]:
    """Create one ``<schema>.<table>_as_of(ts)`` macro per SCD2 table in `schema`.

    Returns the list of macro names created. Idempotent: uses
    ``CREATE OR REPLACE MACRO`` so re-running just refreshes the definitions.
    Macros that already exist for tables that no longer have SCD2 columns
    are left alone -- the caller can ``DROP MACRO`` them explicitly if needed.
    """
    tables = find_scd2_tables(con, schema)
    created: list[str] = []
    for table in tables:
        qschema = _quote(schema)
        qtable = _quote(table)
        macro_name = f"{table}_as_of"
        qmacro = _quote(macro_name)
        sql = (
            f"CREATE OR REPLACE MACRO {qschema}.{qmacro}(ts) AS TABLE "
            f"SELECT * FROM {qschema}.{qtable} "
            f"WHERE _dlt_valid_from <= ts "
            f"AND (_dlt_valid_to IS NULL OR _dlt_valid_to > ts)"
        )
        con.execute(sql)
        created.append(f"{schema}.{macro_name}")
    if created:
        logger.info("Created %d AS-OF macros in schema %s: %s", len(created), schema, ", ".join(created))
    return created
