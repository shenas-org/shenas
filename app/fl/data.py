"""Fetch training data from the local shenas server via REST API.

The FL client does not access DuckDB directly. It queries the shenas app
server's /api/query endpoint and gets Arrow IPC data back, which we
convert to numpy arrays for training.
"""

from __future__ import annotations

import logging

import httpx
import numpy as np

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches training data from a local shenas instance."""

    def __init__(self, server_url: str = "http://localhost:7280") -> None:
        self._client = httpx.Client(base_url=server_url, verify=False, timeout=30.0)

    def fetch(self, query: str, features: list[str], target: str) -> tuple[np.ndarray, np.ndarray] | None:
        """Execute a SQL query against the local shenas server and return (X, y).

        The server returns Arrow IPC format. We parse it with pyarrow and
        extract the requested columns as numpy arrays.

        Returns None if no data is available or the server is unreachable.
        """
        try:
            resp = self._client.get("/api/query", params={"sql": query})
            if resp.status_code != 200:
                logger.warning("Query failed (status %d): %s", resp.status_code, resp.text[:200])
                return None

            import pyarrow.ipc

            reader = pyarrow.ipc.open_stream(resp.content)
            table = reader.read_all()

            if table.num_rows == 0:
                logger.info("Query returned no rows")
                return None

            # Extract feature columns
            X_cols = []
            for f in features:
                if f not in table.column_names:
                    logger.warning("Feature column '%s' not in query results", f)
                    return None
                X_cols.append(table.column(f).to_numpy(zero_copy_only=False).astype(np.float32))

            X = np.column_stack(X_cols)

            if target not in table.column_names:
                logger.warning("Target column '%s' not in query results", target)
                return None
            y = table.column(target).to_numpy(zero_copy_only=False).astype(np.float32)

            # Drop rows with NaN
            valid = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            X, y = X[valid], y[valid]

            if len(X) == 0:
                logger.info("No valid rows after NaN filtering")
                return None

            logger.info("Fetched %d training samples (%d features)", len(X), X.shape[1])
            return X, y

        except (httpx.ConnectError, httpx.ConnectTimeout):
            logger.warning("Cannot reach shenas server")
            return None
