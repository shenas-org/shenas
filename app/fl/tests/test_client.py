"""Tests for the Flower client integration."""

from unittest.mock import MagicMock, patch

import numpy as np

from app.fl.client import ShenasClient


def _mock_task() -> dict:
    return {
        "name": "test-task",
        "model": "linear",
        "query": "SELECT 1",
        "features": ["a", "b"],
        "target": "y",
        "epochs": 1,
        "batch_size": 32,
        "learning_rate": 0.001,
    }


class TestShenasClient:
    def test_get_parameters(self) -> None:
        with patch("app.fl.client.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=_mock_task()))
            mock_get.return_value.raise_for_status = MagicMock()

            client = ShenasClient(fl_api_url="http://localhost:8081", task_name="test-task")
            params = client.get_parameters({})

            assert len(params) == 2  # weight + bias for linear model
            assert params[0].shape == (1, 2)  # (1 output, 2 features)
            assert params[1].shape == (1,)  # bias

    def test_fit_with_data(self) -> None:
        with patch("app.fl.client.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=_mock_task()))
            mock_get.return_value.raise_for_status = MagicMock()

            client = ShenasClient(fl_api_url="http://localhost:8081", task_name="test-task")

            # Mock data fetcher
            X = np.random.randn(50, 2).astype(np.float32)
            y = np.random.randn(50).astype(np.float32)
            client.fetcher = MagicMock()
            client.fetcher.fetch.return_value = (X, y)

            init_weights = client.get_parameters({})
            updated_weights, n_samples, metrics = client.fit(init_weights, {})

            assert n_samples == 50
            assert "loss" in metrics
            assert len(updated_weights) == 2

    def test_fit_no_data(self) -> None:
        with patch("app.fl.client.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=_mock_task()))
            mock_get.return_value.raise_for_status = MagicMock()

            client = ShenasClient(fl_api_url="http://localhost:8081", task_name="test-task")
            client.fetcher = MagicMock()
            client.fetcher.fetch.return_value = None

            init_weights = client.get_parameters({})
            _updated_weights, n_samples, _metrics = client.fit(init_weights, {})

            assert n_samples == 0

    def test_evaluate(self) -> None:
        with patch("app.fl.client.httpx.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=_mock_task()))
            mock_get.return_value.raise_for_status = MagicMock()

            client = ShenasClient(fl_api_url="http://localhost:8081", task_name="test-task")

            X = np.random.randn(30, 2).astype(np.float32)
            y = np.random.randn(30).astype(np.float32)
            client.fetcher = MagicMock()
            client.fetcher.fetch.return_value = (X, y)

            params = client.get_parameters({})
            _loss, n_samples, metrics = client.evaluate(params, {})

            assert n_samples == 30
            assert "mae" in metrics
