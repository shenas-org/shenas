"""Tests for the plugin management API endpoints."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.server import app

client = TestClient(app)


# Mock plugin state DB functions for all tests in this module
@pytest.fixture(autouse=True)
def _mock_plugin_state():
    with (
        patch("app.api.plugins.get_plugin_state", return_value=None),
        patch("app.db.upsert_plugin_state"),
        patch("app.db.remove_plugin_state"),
        patch("app.db.is_plugin_enabled", return_value=True),
    ):
        yield


class TestListPlugins:
    def test_list_pipes(self) -> None:
        fake_output = json.dumps(
            [
                {"name": "shenas-pipe-garmin", "version": "0.1.0"},
                {"name": "shenas-pipe-core", "version": "0.1.0"},
                {"name": "shenas-pipe-lunchmoney", "version": "0.2.0"},
                {"name": "unrelated-package", "version": "1.0.0"},
            ]
        )
        mock_result = MagicMock(returncode=0, stdout=fake_output)
        with (
            patch("app.api.plugins.subprocess.run", return_value=mock_result),
            patch("app.api.plugins.check_signature", return_value="no key"),
        ):
            resp = client.get("/api/plugins/pipe")

        assert resp.status_code == 200
        data = resp.json()
        names = [p["name"] for p in data]
        assert "garmin" in names
        assert "lunchmoney" in names
        # core is excluded
        assert "core" not in names
        # unrelated is excluded
        assert len(data) == 2

    def test_list_schemas(self) -> None:
        fake_output = json.dumps(
            [
                {"name": "shenas-schema-fitness", "version": "0.1.3"},
            ]
        )
        mock_result = MagicMock(returncode=0, stdout=fake_output)
        with (
            patch("app.api.plugins.subprocess.run", return_value=mock_result),
            patch("app.api.plugins.check_signature", return_value="unsigned"),
        ):
            resp = client.get("/api/plugins/schema")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "fitness"
        assert data[0]["signature"] == "unsigned"

    def test_list_empty(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="[]")
        with patch("app.api.plugins.subprocess.run", return_value=mock_result):
            resp = client.get("/api/plugins/component")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_invalid_kind(self) -> None:
        resp = client.get("/api/plugins/invalid")
        assert resp.status_code == 400
        assert "Invalid kind" in resp.json()["detail"]

    def test_list_subprocess_failure(self) -> None:
        mock_result = MagicMock(returncode=1)
        with patch("app.api.plugins.subprocess.run", return_value=mock_result):
            resp = client.get("/api/plugins/pipe")
        assert resp.status_code == 500


class TestInstallPlugin:
    def test_install_skip_verify(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="ok")
        with patch("app.api.plugins.subprocess.run", return_value=mock_result):
            resp = client.post("/api/plugins/pipe", json={"names": ["garmin"], "skip_verify": True})

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["ok"] is True
        assert "shenas-pipe-garmin" in results[0]["message"]

    def test_install_core_rejected(self) -> None:
        resp = client.post("/api/plugins/pipe", json={"names": ["core"], "skip_verify": True})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results[0]["ok"] is False
        assert "internal plugin" in results[0]["message"]

    def test_install_multiple(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="ok")
        with patch("app.api.plugins.subprocess.run", return_value=mock_result):
            resp = client.post("/api/plugins/schema", json={"names": ["fitness", "finance"], "skip_verify": True})

        results = resp.json()["results"]
        assert len(results) == 2
        assert all(r["ok"] for r in results)

    def test_install_failure(self) -> None:
        mock_result = MagicMock(returncode=1, stderr="not found")
        with patch("app.api.plugins.subprocess.run", return_value=mock_result):
            resp = client.post("/api/plugins/pipe", json={"names": ["nonexistent"], "skip_verify": True})

        results = resp.json()["results"]
        assert results[0]["ok"] is False

    def test_install_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/invalid", json={"names": ["test"]})
        assert resp.status_code == 400


class TestUninstallPlugin:
    def test_uninstall_success(self) -> None:
        mock_result = MagicMock(returncode=0, stdout="ok")
        with patch("app.api.plugins.subprocess.run", return_value=mock_result):
            resp = client.delete("/api/plugins/pipe/garmin")

        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_uninstall_core_rejected(self) -> None:
        resp = client.delete("/api/plugins/pipe/core")
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
        assert "internal plugin" in resp.json()["message"]

    def test_uninstall_failure(self) -> None:
        mock_result = MagicMock(returncode=1, stderr="not installed")
        with patch("app.api.plugins.subprocess.run", return_value=mock_result):
            resp = client.delete("/api/plugins/pipe/nonexistent")

        assert resp.json()["ok"] is False

    def test_uninstall_invalid_kind(self) -> None:
        resp = client.delete("/api/plugins/invalid/test")
        assert resp.status_code == 400
