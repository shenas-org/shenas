"""Tests for the FL REST API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fl_server.auth import ClientRegistry
from fl_server.models import ModelStore
from fl_server.server import api


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    api.state.store = ModelStore(weights_dir=tmp_path / "weights")
    api.state.registry = ClientRegistry(token_file=tmp_path / "clients.json")
    return TestClient(api)


@pytest.fixture()
def auth_header(client: TestClient) -> dict[str, str]:
    """Register a test client and return the auth header."""
    resp = client.post("/api/fl/clients", params={"name": "test-client"})
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealth:
    def test_health_no_auth(self, client: TestClient) -> None:
        resp = client.get("/api/fl/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAuth:
    def test_tasks_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/fl/tasks")
        assert resp.status_code == 401

    def test_tasks_with_auth(self, client: TestClient, auth_header: dict) -> None:
        resp = client.get("/api/fl/tasks", headers=auth_header)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_invalid_token(self, client: TestClient) -> None:
        resp = client.get("/api/fl/tasks", headers={"Authorization": "Bearer bad"})
        assert resp.status_code == 401

    def test_missing_bearer(self, client: TestClient) -> None:
        resp = client.get("/api/fl/tasks", headers={"Authorization": "bad"})
        assert resp.status_code == 401


class TestClientManagement:
    def test_register_client(self, client: TestClient) -> None:
        resp = client.post("/api/fl/clients", params={"name": "alice"})
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_list_clients(self, client: TestClient) -> None:
        client.post("/api/fl/clients", params={"name": "alice"})
        client.post("/api/fl/clients", params={"name": "bob"})
        resp = client.get("/api/fl/clients")
        assert resp.status_code == 200
        assert sorted(resp.json()) == ["alice", "bob"]

    def test_revoke_client(self, client: TestClient) -> None:
        resp = client.post("/api/fl/clients", params={"name": "alice"})
        token = resp.json()["token"]

        client.delete("/api/fl/clients/alice")
        resp = client.get("/api/fl/tasks", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestTasks:
    def test_get_task(self, client: TestClient, auth_header: dict) -> None:
        resp = client.get("/api/fl/tasks/sleep-forecast", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json()["model"] == "linear"

    def test_get_nonexistent(self, client: TestClient, auth_header: dict) -> None:
        resp = client.get("/api/fl/tasks/nonexistent", headers=auth_header)
        assert resp.status_code == 404


class TestWeights:
    def test_weights_not_found(self, client: TestClient, auth_header: dict) -> None:
        resp = client.get("/api/fl/tasks/sleep-forecast/weights", headers=auth_header)
        assert resp.status_code == 404

    def test_weights_after_save(self, client: TestClient, auth_header: dict) -> None:
        import numpy as np

        store = api.state.store
        store.save("sleep-forecast", 0, [np.array([1.0, 2.0]), np.array([[3.0]])])

        resp = client.get("/api/fl/tasks/sleep-forecast/weights", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["round"] == 0
        assert data["num_arrays"] == 2


class TestHistory:
    def test_empty_history(self, client: TestClient, auth_header: dict) -> None:
        resp = client.get("/api/fl/tasks/sleep-forecast/history", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_rounds(self, client: TestClient, auth_header: dict) -> None:
        import numpy as np

        store = api.state.store
        store.save("sleep-forecast", 0, [np.array([1.0])], num_clients=3)
        store.save("sleep-forecast", 1, [np.array([2.0])], num_clients=5)

        resp = client.get("/api/fl/tasks/sleep-forecast/history", headers=auth_header)
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 2
        assert history[0]["round"] == 0
        assert history[0]["num_clients"] == 3
        assert history[1]["round"] == 1
        assert "timestamp" in history[1]
