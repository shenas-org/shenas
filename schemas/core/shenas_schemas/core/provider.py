from typing import Protocol

import duckdb


class MetricProvider(Protocol):
    """Each pipe implements this to write into the canonical metrics schema."""

    source: str

    def transform(self, con: duckdb.DuckDBPyConnection) -> None:
        """Read from the provider's raw schema and write into metrics.*."""
        ...
