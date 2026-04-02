"""Tests for data fetching (Arrow IPC format)."""

from unittest.mock import MagicMock, patch

import pyarrow as pa

from app.fl.data import DataFetcher


def _make_arrow_response(table: pa.Table) -> MagicMock:
    """Create a mock HTTP response containing Arrow IPC data."""
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    resp = MagicMock()
    resp.status_code = 200
    resp.content = sink.getvalue().to_pybytes()
    return resp


class TestDataFetcher:
    def test_fetch_success(self) -> None:
        table = pa.table(
            {
                "rmssd": [40.0, 45.0],
                "sdnn": [50.0, 55.0],
                "target": [75.0, 80.0],
            }
        )
        mock_resp = _make_arrow_response(table)

        fetcher = DataFetcher()
        with patch.object(fetcher._client, "get", return_value=mock_resp):
            result = fetcher.fetch("SELECT 1", ["rmssd", "sdnn"], "target")

        assert result is not None
        X, y = result
        assert X.shape == (2, 2)
        assert y.shape == (2,)
        assert y[0] == 75.0

    def test_fetch_empty(self) -> None:
        table = pa.table({"a": pa.array([], type=pa.float64()), "y": pa.array([], type=pa.float64())})
        mock_resp = _make_arrow_response(table)

        fetcher = DataFetcher()
        with patch.object(fetcher._client, "get", return_value=mock_resp):
            result = fetcher.fetch("SELECT 1", ["a"], "y")

        assert result is None

    def test_fetch_server_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal error"

        fetcher = DataFetcher()
        with patch.object(fetcher._client, "get", return_value=mock_resp):
            result = fetcher.fetch("SELECT 1", ["a"], "y")

        assert result is None

    def test_fetch_missing_feature_column(self) -> None:
        table = pa.table({"a": [1.0], "target": [2.0]})
        mock_resp = _make_arrow_response(table)

        fetcher = DataFetcher()
        with patch.object(fetcher._client, "get", return_value=mock_resp):
            result = fetcher.fetch("SELECT 1", ["a", "missing_col"], "target")

        assert result is None

    def test_fetch_nan_filtered(self) -> None:
        table = pa.table(
            {
                "a": [1.0, float("nan"), 4.0],
                "target": [2.0, 3.0, float("nan")],
            }
        )
        mock_resp = _make_arrow_response(table)

        fetcher = DataFetcher()
        with patch.object(fetcher._client, "get", return_value=mock_resp):
            result = fetcher.fetch("SELECT 1", ["a"], "target")

        assert result is not None
        X, y = result
        assert len(X) == 1  # only the first row has no NaN
        assert y[0] == 2.0
