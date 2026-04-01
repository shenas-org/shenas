"""Flower client that trains on local shenas data.

Connects to the central Flower server, fetches task definitions from the
FL REST API, queries the local shenas instance for training data, trains
locally, and returns weight updates.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from flwr.client import NumPyClient
from flwr.common import NDArrays

from fl_client.data import DataFetcher
from fl_client.trainer import evaluate, get_model, get_weights, set_weights, train

logger = logging.getLogger(__name__)


class ShenasClient(NumPyClient):
    """Flower client that trains on local shenas data."""

    def __init__(
        self,
        fl_api_url: str,
        task_name: str,
        shenas_url: str = "http://localhost:7280",
    ) -> None:
        self.fl_api_url = fl_api_url
        self.task_name = task_name
        self.fetcher = DataFetcher(server_url=shenas_url)
        self.model: Any = None
        self._task: dict[str, Any] | None = None

    def _get_task(self) -> dict[str, Any]:
        """Fetch task definition from the FL server REST API."""
        if self._task is None:
            resp = httpx.get(f"{self.fl_api_url}/api/fl/tasks/{self.task_name}", timeout=10.0)
            resp.raise_for_status()
            self._task = resp.json()
        return self._task

    def _ensure_model(self, n_features: int) -> None:
        """Create the model if it doesn't exist yet."""
        if self.model is None:
            task = self._get_task()
            self.model = get_model(task["model"], n_features)

    def get_parameters(self, config: dict[str, Any]) -> NDArrays:
        """Return current model weights."""
        task = self._get_task()
        n_features = len(task["features"])
        self._ensure_model(n_features)
        return get_weights(self.model)

    def fit(self, parameters: NDArrays, config: dict[str, Any]) -> tuple[NDArrays, int, dict[str, float]]:
        """Train on local data and return updated weights."""
        task = self._get_task()
        data = self.fetcher.fetch(task["query"], task["features"], task["target"])

        if data is None:
            logger.warning("No training data available, returning unchanged weights")
            return parameters, 0, {"loss": 0.0}

        X, y = data
        self._ensure_model(X.shape[1])
        set_weights(self.model, parameters)

        metrics = train(
            self.model,
            X,
            y,
            epochs=task.get("epochs", 3),
            batch_size=task.get("batch_size", 32),
            lr=task.get("learning_rate", 0.001),
        )

        return get_weights(self.model), len(X), metrics

    def evaluate(self, parameters: NDArrays, config: dict[str, Any]) -> tuple[float, int, dict[str, float]]:
        """Evaluate model on local data."""
        task = self._get_task()
        data = self.fetcher.fetch(task["query"], task["features"], task["target"])

        if data is None:
            return 0.0, 0, {"loss": 0.0}

        X, y = data
        self._ensure_model(X.shape[1])
        set_weights(self.model, parameters)

        metrics = evaluate(self.model, X, y)
        return metrics["loss"], len(X), metrics
