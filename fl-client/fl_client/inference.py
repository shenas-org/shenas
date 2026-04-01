"""Local inference using the latest global model weights.

Downloads weights from the FL server, loads them into the model plugin,
and runs predictions on local data fetched from the shenas app server.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
import numpy as np
import torch

from fl_client.data import DataFetcher
from fl_client.trainer import get_model, set_weights

logger = logging.getLogger(__name__)

WEIGHTS_CACHE = Path(".shenas-fl/client-weights")


class InferenceEngine:
    """Runs predictions using the latest global model."""

    def __init__(
        self,
        fl_api_url: str = "http://127.0.0.1:8081",
        shenas_url: str = "http://localhost:7280",
    ) -> None:
        self.fl_api_url = fl_api_url
        self.fetcher = DataFetcher(server_url=shenas_url)
        self._models: dict[str, torch.nn.Module] = {}
        self._rounds: dict[str, int] = {}

    def _fetch_weights(self, task_name: str) -> tuple[list[np.ndarray], int] | None:
        """Download latest weights from FL server REST API."""
        try:
            resp = httpx.get(f"{self.fl_api_url}/api/fl/tasks/{task_name}/weights", timeout=10.0)
            if resp.status_code != 200:
                return None

            meta = resp.json()
            round_num = meta["round"]

            # Check if we already have this round cached
            if self._rounds.get(task_name) == round_num:
                return None  # already up to date

            # Download actual weight arrays from the FL server's model store
            # For now, we use the metadata to know the shapes and reconstruct
            # In production, this would be a separate binary endpoint
            # For Phase 3, we read from the shared weights dir if co-located
            weights_dir = WEIGHTS_CACHE / task_name
            weights_dir.mkdir(parents=True, exist_ok=True)

            # Try loading from shared FL server weights (works when co-located)
            server_weights = Path(f".shenas-fl/weights/{task_name}/latest.npz")
            if server_weights.exists():
                data = np.load(server_weights)
                weights = [data[k] for k in sorted(data.files)]
                self._rounds[task_name] = round_num
                return weights, round_num

            return None
        except Exception:
            logger.warning("Failed to fetch weights for %s", task_name, exc_info=True)
            return None

    def predict(self, task_name: str) -> dict | None:
        """Run prediction for a task using latest global model and local data.

        Returns a dict with predictions and metadata, or None if unavailable.
        """
        # Get task info
        try:
            resp = httpx.get(f"{self.fl_api_url}/api/fl/tasks/{task_name}", timeout=10.0)
            if resp.status_code != 200:
                return None
            task = resp.json()
        except Exception:
            return None

        features = task["features"]
        target = task["target"]
        model_name = task["model"]

        # Ensure model is loaded with latest weights
        result = self._fetch_weights(task_name)
        if result is not None:
            weights, round_num = result
            model = get_model(model_name, len(features))
            set_weights(model, weights)
            self._models[task_name] = model
            logger.info("Updated model for %s to round %d", task_name, round_num)

        model = self._models.get(task_name)
        if model is None:
            return None

        # Fetch recent data for prediction
        # Use the same query but get the latest rows
        data = self.fetcher.fetch(task["query"], features, target)
        if data is None:
            return None

        X, y_actual = data
        model.eval()

        # Normalize
        X_t = torch.tensor(X, dtype=torch.float32)
        mean = X_t.mean(dim=0)
        std = X_t.std(dim=0).clamp(min=1e-6)
        X_t = (X_t - mean) / std

        with torch.no_grad():
            predictions = model(X_t).numpy()

        return {
            "task": task_name,
            "model": model_name,
            "round": self._rounds.get(task_name),
            "n_samples": len(predictions),
            "predictions": predictions.tolist()[-5:],  # last 5 predictions
            "actuals": y_actual.tolist()[-5:],  # last 5 actuals for comparison
            "mae": float(np.abs(predictions - y_actual).mean()),
        }

    def list_available(self) -> list[dict]:
        """List models that have weights available."""
        models = []
        try:
            resp = httpx.get(f"{self.fl_api_url}/api/fl/tasks", timeout=10.0)
            if resp.status_code != 200:
                return []
            for task in resp.json():
                if task.get("latest_round") is not None:
                    models.append(
                        {
                            "name": task["name"],
                            "description": task.get("description", ""),
                            "round": task["latest_round"],
                            "features": task["features"],
                            "target": task["target"],
                        }
                    )
        except Exception:
            pass
        return models
