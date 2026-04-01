"""Tests for the inference REST API."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from fl_client.api import api
from fl_client.inference import InferenceEngine


def _make_client() -> TestClient:
    api.state.engine = MagicMock(spec=InferenceEngine)
    return TestClient(api)


class TestInferenceAPI:
    def test_health(self) -> None:
        client = _make_client()
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_list_models(self) -> None:
        client = _make_client()
        api.state.engine.list_available.return_value = [
            {"name": "sleep-forecast", "round": 3, "features": ["rmssd"], "target": "score"}
        ]
        resp = client.get("/api/models")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_predict_available(self) -> None:
        client = _make_client()
        api.state.engine.predict.return_value = {
            "task": "sleep-forecast",
            "model": "linear",
            "round": 3,
            "n_samples": 5,
            "predictions": [75.0, 78.0],
            "actuals": [74.0, 80.0],
            "mae": 2.0,
        }
        resp = client.get("/api/models/sleep-forecast/predict")
        assert resp.status_code == 200
        assert resp.json()["mae"] == 2.0

    def test_predict_not_available(self) -> None:
        client = _make_client()
        api.state.engine.predict.return_value = None
        resp = client.get("/api/models/sleep-forecast/predict")
        assert resp.status_code == 404

    def test_model_status(self) -> None:
        client = _make_client()
        api.state.engine.list_available.return_value = [
            {"name": "sleep-forecast", "round": 5, "features": [], "target": "score"}
        ]
        resp = client.get("/api/models/sleep-forecast/status")
        assert resp.status_code == 200
        assert resp.json()["available"] is True
        assert resp.json()["round"] == 5
