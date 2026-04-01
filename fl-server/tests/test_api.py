"""Tests for the FL REST API."""

from pathlib import Path

from fastapi.testclient import TestClient

from fl_server.models import ModelStore
from fl_server.server import api


def _make_client(tmp_path: Path) -> TestClient:
    api.state.store = ModelStore(weights_dir=tmp_path / "weights")
    return TestClient(api)


class TestAPI:
    def test_health(self, tmp_path: Path) -> None:
        client = _make_client(tmp_path)
        resp = client.get("/api/fl/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["tasks"] >= 1

    def test_list_tasks(self, tmp_path: Path) -> None:
        client = _make_client(tmp_path)
        resp = client.get("/api/fl/tasks")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) >= 1
        assert tasks[0]["name"] == "sleep-forecast"

    def test_get_task(self, tmp_path: Path) -> None:
        client = _make_client(tmp_path)
        resp = client.get("/api/fl/tasks/sleep-forecast")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "linear"
        assert "rmssd" in data["features"]

    def test_get_nonexistent_task(self, tmp_path: Path) -> None:
        client = _make_client(tmp_path)
        resp = client.get("/api/fl/tasks/nonexistent")
        assert resp.status_code == 404

    def test_weights_not_found(self, tmp_path: Path) -> None:
        client = _make_client(tmp_path)
        resp = client.get("/api/fl/tasks/sleep-forecast/weights")
        assert resp.status_code == 404

    def test_weights_after_save(self, tmp_path: Path) -> None:
        import numpy as np

        client = _make_client(tmp_path)
        store = api.state.store
        store.save("sleep-forecast", 0, [np.array([1.0, 2.0]), np.array([[3.0]])])

        resp = client.get("/api/fl/tasks/sleep-forecast/weights")
        assert resp.status_code == 200
        data = resp.json()
        assert data["round"] == 0
        assert data["num_arrays"] == 2
        assert data["total_params"] == 3
