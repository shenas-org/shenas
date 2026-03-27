import duckdb


class MetricProviderBase:
    """Base class for pipe transform providers. Subclass and set `source`."""

    source: str

    def _upsert(self, con: duckdb.DuckDBPyConnection, table: str, insert_sql: str) -> None:
        """Delete existing rows for this source, then insert new data."""
        con.execute(f"DELETE FROM metrics.{table} WHERE source = '{self.source}'")
        con.execute(insert_sql)
