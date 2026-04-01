"""Tests for data fetching."""

from unittest.mock import MagicMock, patch

from app.fl.data import DataFetcher


class TestDataFetcher:
    def test_fetch_success(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"rmssd": 40.0, "sdnn": 50.0, "target": 75.0},
            {"rmssd": 45.0, "sdnn": 55.0, "target": 80.0},
        ]

        fetcher = DataFetcher()
        with patch.object(fetcher._client, "get", return_value=mock_resp):
            result = fetcher.fetch("SELECT 1", ["rmssd", "sdnn"], "target")

        assert result is not None
        X, y = result
        assert X.shape == (2, 2)
        assert y.shape == (2,)
        assert y[0] == 75.0

    def test_fetch_empty(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

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

    def test_fetch_null_values_filtered(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"a": 1.0, "target": 2.0},
            {"a": None, "target": 3.0},
            {"a": 4.0, "target": None},
        ]

        fetcher = DataFetcher()
        with patch.object(fetcher._client, "get", return_value=mock_resp):
            result = fetcher.fetch("SELECT 1", ["a"], "target")

        assert result is not None
        X, y = result
        # None becomes 0.0 which is valid (not NaN), so all 3 rows pass
        assert len(X) == 3
