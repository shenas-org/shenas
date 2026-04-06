"""Tests for the plugins API endpoints and helpers."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.plugins import (
    VALID_KINDS,
    _prefix,
    _sse,
    _validate_kind,
    check_signature,
    install_plugin,
    list_plugins_data,
    uninstall_plugin,
)
from app.server import app
from app.tests.conftest import parse_sse

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakePluginCls:
    """Minimal stand-in for a plugin class returned by _load_plugin."""

    internal = False
    enabled_by_default = True

    def __init__(self) -> None:
        pass

    def get_info(self) -> dict:
        return {
            "display_name": "Fake Plugin",
            "description": "A fake plugin for testing",
            "commands": ["sync"],
            "has_config": True,
            "has_data": True,
            "has_auth": False,
            "is_authenticated": None,
            "sync_frequency": 3600,
        }

    def enable(self) -> str:
        return "enabled"

    def disable(self) -> str:
        return "disabled"


class _InternalPluginCls(_FakePluginCls):
    internal = True


# ---------------------------------------------------------------------------
# _prefix
# ---------------------------------------------------------------------------


class TestPrefix:
    def test_pipe(self) -> None:
        assert _prefix("pipe") == "shenas-pipe-"

    def test_schema(self) -> None:
        assert _prefix("schema") == "shenas-schema-"

    def test_component(self) -> None:
        assert _prefix("component") == "shenas-component-"


# ---------------------------------------------------------------------------
# _validate_kind
# ---------------------------------------------------------------------------


class TestValidateKind:
    def test_valid_kinds(self) -> None:
        for kind in VALID_KINDS:
            _validate_kind(kind)  # should not raise

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _validate_kind("invalid")
        assert exc_info.value.status_code == 400
        assert "Invalid kind" in exc_info.value.detail

    def test_invalid_kind_lists_valid(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _validate_kind("bogus")
        for kind in VALID_KINDS:
            assert kind in exc_info.value.detail


# ---------------------------------------------------------------------------
# _sse
# ---------------------------------------------------------------------------


class TestSse:
    def test_format(self) -> None:
        result = _sse("log", text="hello")
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        data = json.loads(result[6:].strip())
        assert data["event"] == "log"
        assert data["text"] == "hello"

    def test_done_event(self) -> None:
        result = _sse("done", ok=True, message="finished")
        data = json.loads(result[6:].strip())
        assert data["ok"] is True
        assert data["message"] == "finished"


# ---------------------------------------------------------------------------
# check_signature
# ---------------------------------------------------------------------------


class TestCheckSignature:
    def test_no_key_file(self, tmp_path: Path) -> None:
        with patch("app.api.plugins.PUBLIC_KEY_PATH", tmp_path / "missing.pub"):
            assert check_signature("shenas-pipe-test", "1.0.0") == "no key"

    def test_no_packages_dir(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        with (
            patch("app.api.plugins.PUBLIC_KEY_PATH", key_path),
            patch("app.api.plugins.PACKAGES_DIR", tmp_path / "nonexistent"),
        ):
            assert check_signature("shenas-pipe-test", "1.0.0") == "unsigned"

    def test_no_matching_wheel(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        packages = tmp_path / "packages"
        packages.mkdir()
        with (
            patch("app.api.plugins.PUBLIC_KEY_PATH", key_path),
            patch("app.api.plugins.PACKAGES_DIR", packages),
        ):
            assert check_signature("shenas-pipe-test", "1.0.0") == "unsigned"

    def test_no_sig_file(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        packages = tmp_path / "packages"
        packages.mkdir()
        (packages / "shenas_pipe_test-1.0.0-py3-none-any.whl").write_bytes(b"wheeldata")
        with (
            patch("app.api.plugins.PUBLIC_KEY_PATH", key_path),
            patch("app.api.plugins.PACKAGES_DIR", packages),
        ):
            assert check_signature("shenas-pipe-test", "1.0.0") == "unsigned"

    def test_valid_signature(self, tmp_path: Path) -> None:
        import base64

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

        key_path = tmp_path / "shenas.pub"
        key_path.write_bytes(pem)

        packages = tmp_path / "packages"
        packages.mkdir()
        wheel = packages / "shenas_pipe_test-1.0.0-py3-none-any.whl"
        wheel_data = b"fake wheel content"
        wheel.write_bytes(wheel_data)

        sig = base64.b64encode(private_key.sign(wheel_data)).decode()
        sig_path = wheel.with_suffix(wheel.suffix + ".sig")
        sig_path.write_text(sig)

        with (
            patch("app.api.plugins.PUBLIC_KEY_PATH", key_path),
            patch("app.api.plugins.PACKAGES_DIR", packages),
        ):
            assert check_signature("shenas-pipe-test", "1.0.0") == "valid"

    def test_invalid_signature(self, tmp_path: Path) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pem = public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

        key_path = tmp_path / "shenas.pub"
        key_path.write_bytes(pem)

        packages = tmp_path / "packages"
        packages.mkdir()
        wheel = packages / "shenas_pipe_test-1.0.0-py3-none-any.whl"
        wheel.write_bytes(b"wheel content")

        sig_path = wheel.with_suffix(wheel.suffix + ".sig")
        sig_path.write_text("bm90YXNpZw==")  # base64("notasig")

        with (
            patch("app.api.plugins.PUBLIC_KEY_PATH", key_path),
            patch("app.api.plugins.PACKAGES_DIR", packages),
        ):
            assert check_signature("shenas-pipe-test", "1.0.0") == "invalid"


# ---------------------------------------------------------------------------
# list_plugins_data
# ---------------------------------------------------------------------------


class TestListPluginsData:
    def test_empty_list(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
        ):
            result = list_plugins_data("pipe")
        assert result == []

    def test_filters_by_prefix(self) -> None:
        installed = [
            {"name": "shenas-pipe-garmin", "version": "1.0.0"},
            {"name": "shenas-schema-fitness", "version": "1.0.0"},
            {"name": "unrelated-package", "version": "0.1.0"},
        ]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        fake_cls = _FakePluginCls
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=fake_cls),
            patch("app.api.pipes._load_plugin_fresh", return_value=fake_cls),
            patch("app.api.plugins.check_signature", return_value="unsigned"),
            patch("app.api.plugins.get_plugin_state", return_value=None),
        ):
            result = list_plugins_data("pipe")
        assert len(result) == 1
        assert result[0].name == "garmin"

    def test_skips_core(self) -> None:
        installed = [
            {"name": "shenas-pipe-core", "version": "1.0.0"},
            {"name": "shenas-pipe-garmin", "version": "1.0.0"},
        ]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        fake_cls = _FakePluginCls
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=fake_cls),
            patch("app.api.pipes._load_plugin_fresh", return_value=fake_cls),
            patch("app.api.plugins.check_signature", return_value="unsigned"),
            patch("app.api.plugins.get_plugin_state", return_value=None),
        ):
            result = list_plugins_data("pipe")
        names = [r.name for r in result]
        assert "core" not in names
        assert "garmin" in names

    def test_skips_internal(self) -> None:
        installed = [{"name": "shenas-pipe-internal", "version": "1.0.0"}]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=_InternalPluginCls),
            patch("app.api.pipes._load_plugin_fresh", return_value=_InternalPluginCls),
            patch("app.api.plugins.check_signature", return_value="unsigned"),
            patch("app.api.plugins.get_plugin_state", return_value=None),
        ):
            result = list_plugins_data("pipe")
        assert len(result) == 0

    def test_no_plugin_cls_fallback(self) -> None:
        installed = [{"name": "shenas-pipe-mystery", "version": "1.0.0"}]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.pipes._load_plugin_fresh", return_value=None),
            patch("app.api.plugins.check_signature", return_value="unsigned"),
            patch("app.api.plugins.get_plugin_state", return_value=None),
        ):
            result = list_plugins_data("pipe")
        assert len(result) == 1
        assert result[0].name == "mystery"
        assert result[0].display_name == "Mystery"
        assert result[0].enabled is True

    def test_subprocess_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                list_plugins_data("pipe")
            assert exc_info.value.status_code == 500

    def test_uses_plugin_state_when_available(self) -> None:
        installed = [{"name": "shenas-pipe-garmin", "version": "1.0.0"}]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        state = {"enabled": False, "added_at": "2026-01-01", "updated_at": None, "status_changed_at": None, "synced_at": None}
        fake_cls = _FakePluginCls
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=fake_cls),
            patch("app.api.pipes._load_plugin_fresh", return_value=fake_cls),
            patch("app.api.plugins.check_signature", return_value="unsigned"),
            patch("app.api.plugins.get_plugin_state", return_value=state),
        ):
            result = list_plugins_data("pipe")
        assert result[0].enabled is False
        assert result[0].added_at == "2026-01-01"


# ---------------------------------------------------------------------------
# install_plugin
# ---------------------------------------------------------------------------


class TestInstallPlugin:
    def test_install_success(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.pipes._clear_caches"),
            patch("app.db.upsert_plugin_state") as mock_upsert,
        ):
            result = install_plugin("garmin", "pipe", skip_verify=True)
        assert result.ok is True
        assert result.name == "garmin"
        assert "Garmin" in result.message
        mock_upsert.assert_called_once_with("pipe", "garmin", enabled=True)

    def test_install_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Resolution failed")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=None),
        ):
            result = install_plugin("nonexistent", "pipe", skip_verify=True)
        assert result.ok is False
        assert "Resolution failed" in result.message

    def test_install_internal_blocked(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=_InternalPluginCls):
            result = install_plugin("internal", "pipe", skip_verify=True)
        assert result.ok is False
        assert "internal plugin" in result.message

    def test_install_core_blocked(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=None):
            result = install_plugin("core", "pipe", skip_verify=True)
        assert result.ok is False
        assert "internal plugin" in result.message

    def test_install_verify_no_key(self, tmp_path: Path) -> None:
        with (
            patch("app.api.plugins.PUBLIC_KEY_PATH", tmp_path / "missing.pub"),
            patch("app.api.pipes._load_plugin", return_value=None),
        ):
            result = install_plugin("garmin", "pipe", public_key_path=tmp_path / "missing.pub")
        assert result.ok is False
        assert "Public key not found" in result.message

    def test_install_verify_fails(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        with (
            patch("app.api.plugins.PUBLIC_KEY_PATH", key_path),
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.plugins._load_public_key", return_value=MagicMock()),
            patch("app.api.plugins._verify_from_index", return_value="No signature found"),
        ):
            result = install_plugin("garmin", "pipe", public_key_path=key_path)
        assert result.ok is False
        assert "No signature found" in result.message


# ---------------------------------------------------------------------------
# uninstall_plugin
# ---------------------------------------------------------------------------


class TestUninstallPlugin:
    def test_uninstall_success(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.pipes._clear_caches"),
            patch("app.db.remove_plugin_state") as mock_remove,
        ):
            result = uninstall_plugin("garmin", "pipe")
        assert result.ok is True
        assert "Garmin" in result.message
        mock_remove.assert_called_once_with("pipe", "garmin")

    def test_uninstall_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Not installed")
        with (
            patch("app.api.plugins.subprocess.run", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._load_plugin", return_value=None),
        ):
            result = uninstall_plugin("nonexistent", "pipe")
        assert result.ok is False
        assert "Not installed" in result.message

    def test_uninstall_internal_blocked(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=_InternalPluginCls):
            result = uninstall_plugin("internal", "pipe")
        assert result.ok is False
        assert "internal plugin" in result.message

    def test_uninstall_core_blocked(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=None):
            result = uninstall_plugin("core", "pipe")
        assert result.ok is False
        assert "internal plugin" in result.message


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


class TestListPluginsEndpoint:
    def test_valid_kind(self) -> None:
        with patch("app.api.plugins.list_plugins_data", return_value=[]):
            resp = client.get("/api/plugins/pipe")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invalid_kind(self) -> None:
        resp = client.get("/api/plugins/bogus")
        assert resp.status_code == 400


class TestAddPluginsEndpoint:
    def test_add_single(self) -> None:
        from app.models import InstallResult

        mock_result = InstallResult(name="garmin", ok=True, message="Added Garmin Pipe")
        with patch("app.api.plugins.install_plugin", return_value=mock_result) as mock_install:
            resp = client.post("/api/plugins/pipe", json={"names": ["garmin"], "skip_verify": True})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["ok"] is True
        mock_install.assert_called_once()

    def test_add_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/bogus", json={"names": ["test"]})
        assert resp.status_code == 400


class TestRemovePluginEndpoint:
    def test_remove(self) -> None:
        from app.models import RemoveResponse

        mock_resp = RemoveResponse(ok=True, message="Removed Garmin Pipe")
        with patch("app.api.plugins.uninstall_plugin", return_value=mock_resp):
            resp = client.delete("/api/plugins/pipe/garmin")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_remove_invalid_kind(self) -> None:
        resp = client.delete("/api/plugins/bogus/garmin")
        assert resp.status_code == 400


class TestEnablePluginEndpoint:
    def test_enable(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=_FakePluginCls):
            resp = client.post("/api/plugins/pipe/garmin/enable")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_enable_not_found(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=None):
            resp = client.post("/api/plugins/pipe/garmin/enable")
        assert resp.status_code == 404

    def test_enable_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/bogus/garmin/enable")
        assert resp.status_code == 400


class TestDisablePluginEndpoint:
    def test_disable(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=_FakePluginCls):
            resp = client.post("/api/plugins/pipe/garmin/disable")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_disable_not_found(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=None):
            resp = client.post("/api/plugins/pipe/garmin/disable")
        assert resp.status_code == 404

    def test_disable_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/bogus/garmin/disable")
        assert resp.status_code == 400


class TestPluginInfoEndpoint:
    def test_info(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=_FakePluginCls):
            resp = client.get("/api/plugins/pipe/garmin/info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Fake Plugin"

    def test_info_not_found(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=None):
            resp = client.get("/api/plugins/pipe/garmin/info")
        assert resp.status_code == 404

    def test_info_invalid_kind(self) -> None:
        resp = client.get("/api/plugins/bogus/garmin/info")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Streaming endpoints
# ---------------------------------------------------------------------------


class TestInstallStream:
    def test_install_stream_internal_blocked(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=_InternalPluginCls):
            resp = client.post(
                "/api/plugins/pipe/install-stream",
                json={"names": ["internal"], "skip_verify": True},
            )
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert len(done) == 1
        assert done[0]["ok"] is False
        assert "internal plugin" in done[0]["message"]

    def test_install_stream_success(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="Installed ok\n")
        with (
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._clear_caches"),
            patch("app.db.upsert_plugin_state"),
        ):
            resp = client.post(
                "/api/plugins/pipe/install-stream",
                json={"names": ["garmin"], "skip_verify": True},
            )
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert len(done) == 1
        assert done[0]["ok"] is True

    def test_install_stream_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Resolution failed\n")
        with (
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
        ):
            resp = client.post(
                "/api/plugins/pipe/install-stream",
                json={"names": ["nonexistent"], "skip_verify": True},
            )
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert done[0]["ok"] is False

    def test_install_stream_no_name(self) -> None:
        resp = client.post("/api/plugins/pipe/install-stream", json={"names": []})
        assert resp.status_code == 400

    def test_install_stream_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/bogus/install-stream", json={"names": ["test"]})
        assert resp.status_code == 400


class TestRemoveStream:
    def test_remove_stream_internal_blocked(self) -> None:
        with patch("app.api.pipes._load_plugin", return_value=_InternalPluginCls):
            resp = client.post("/api/plugins/pipe/internal/remove-stream")
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert len(done) == 1
        assert done[0]["ok"] is False

    def test_remove_stream_success(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="Uninstalled\n")
        with (
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.pipes._clear_caches"),
            patch("app.db.remove_plugin_state"),
        ):
            resp = client.post("/api/plugins/pipe/garmin/remove-stream")
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert done[0]["ok"] is True

    def test_remove_stream_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Not found\n")
        with (
            patch("app.api.pipes._load_plugin", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
        ):
            resp = client.post("/api/plugins/pipe/garmin/remove-stream")
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert done[0]["ok"] is False

    def test_remove_stream_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/bogus/garmin/remove-stream")
        assert resp.status_code == 400
