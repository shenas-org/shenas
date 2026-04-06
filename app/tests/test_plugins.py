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
    _sse,
    _validate_kind,
)
from app.server import app
from app.tests.conftest import parse_sse
from shenas_plugins.core.plugin import (
    VALID_KINDS,
    Plugin,
    _check_signature,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakePluginCls:
    """Minimal stand-in for a plugin class returned by _load_plugin."""

    internal = False
    enabled_by_default = True
    has_config = True

    def __init__(self) -> None:
        pass

    def get_config_entries(self) -> list:
        return []

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
# _check_signature
# ---------------------------------------------------------------------------


class TestCheckSignature:
    def test_no_key_file(self, tmp_path: Path) -> None:
        with patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", tmp_path / "missing.pub"):
            assert _check_signature("shenas-source-test", "1.0.0") == "no key"

    def test_no_packages_dir(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        with (
            patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", key_path),
            patch("shenas_plugins.core.plugin.PACKAGES_DIR", tmp_path / "nonexistent"),
        ):
            assert _check_signature("shenas-source-test", "1.0.0") == "unsigned"

    def test_no_matching_wheel(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        packages = tmp_path / "packages"
        packages.mkdir()
        with (
            patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", key_path),
            patch("shenas_plugins.core.plugin.PACKAGES_DIR", packages),
        ):
            assert _check_signature("shenas-source-test", "1.0.0") == "unsigned"

    def test_no_sig_file(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        packages = tmp_path / "packages"
        packages.mkdir()
        (packages / "shenas_source_test-1.0.0-py3-none-any.whl").write_bytes(b"wheeldata")
        with (
            patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", key_path),
            patch("shenas_plugins.core.plugin.PACKAGES_DIR", packages),
        ):
            assert _check_signature("shenas-source-test", "1.0.0") == "unsigned"

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
        wheel = packages / "shenas_source_test-1.0.0-py3-none-any.whl"
        wheel_data = b"fake wheel content"
        wheel.write_bytes(wheel_data)

        sig = base64.b64encode(private_key.sign(wheel_data)).decode()
        sig_path = wheel.with_suffix(wheel.suffix + ".sig")
        sig_path.write_text(sig)

        with (
            patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", key_path),
            patch("shenas_plugins.core.plugin.PACKAGES_DIR", packages),
        ):
            assert _check_signature("shenas-source-test", "1.0.0") == "valid"

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
        wheel = packages / "shenas_source_test-1.0.0-py3-none-any.whl"
        wheel.write_bytes(b"wheel content")

        sig_path = wheel.with_suffix(wheel.suffix + ".sig")
        sig_path.write_text("bm90YXNpZw==")  # base64("notasig")

        with (
            patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", key_path),
            patch("shenas_plugins.core.plugin.PACKAGES_DIR", packages),
        ):
            assert _check_signature("shenas-source-test", "1.0.0") == "invalid"


# ---------------------------------------------------------------------------
# Plugin.list_installed
# ---------------------------------------------------------------------------


class TestListPluginsData:
    def test_empty_list(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
        ):
            result = Plugin.list_installed("source")
        assert result == []

    def test_filters_by_prefix(self) -> None:
        installed = [
            {"name": "shenas-source-garmin", "version": "1.0.0"},
            {"name": "shenas-dataset-fitness", "version": "1.0.0"},
            {"name": "unrelated-package", "version": "0.1.0"},
        ]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        fake_cls = _FakePluginCls
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=fake_cls),
            patch("app.api.sources._load_plugin_fresh", return_value=fake_cls),
            patch("shenas_plugins.core.plugin._check_signature", return_value="unsigned"),
        ):
            result = Plugin.list_installed("source")
        assert len(result) == 1
        assert result[0]["name"] == "garmin"

    def test_skips_core(self) -> None:
        installed = [
            {"name": "shenas-source-core", "version": "1.0.0"},
            {"name": "shenas-source-garmin", "version": "1.0.0"},
        ]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        fake_cls = _FakePluginCls
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=fake_cls),
            patch("app.api.sources._load_plugin_fresh", return_value=fake_cls),
            patch("shenas_plugins.core.plugin._check_signature", return_value="unsigned"),
        ):
            result = Plugin.list_installed("source")
        names = [r["name"] for r in result]
        assert "core" not in names
        assert "garmin" in names

    def test_skips_internal(self) -> None:
        installed = [{"name": "shenas-source-internal", "version": "1.0.0"}]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=_InternalPluginCls),
            patch("app.api.sources._load_plugin_fresh", return_value=_InternalPluginCls),
            patch("shenas_plugins.core.plugin._check_signature", return_value="unsigned"),
        ):
            result = Plugin.list_installed("source")
        assert len(result) == 0

    def test_no_plugin_cls_fallback(self) -> None:
        installed = [{"name": "shenas-source-mystery", "version": "1.0.0"}]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.sources._load_plugin_fresh", return_value=None),
            patch("shenas_plugins.core.plugin._check_signature", return_value="unsigned"),
        ):
            result = Plugin.list_installed("source")
        assert len(result) == 1
        assert result[0]["name"] == "mystery"
        assert result[0]["display_name"] == "Mystery"
        assert result[0]["enabled"] is True

    def test_subprocess_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
        ):
            assert Plugin.list_installed("source") == []

    def test_uses_plugin_state_when_available(self) -> None:
        installed = [{"name": "shenas-source-garmin", "version": "1.0.0"}]
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(installed), stderr="")

        class _StatefulPlugin(_FakePluginCls):
            def get_info(self):
                info = super().get_info()
                info.update({"enabled": False, "added_at": "2026-01-01"})
                return info

        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=_StatefulPlugin),
            patch("app.api.sources._load_plugin_fresh", return_value=_StatefulPlugin),
            patch("shenas_plugins.core.plugin._check_signature", return_value="unsigned"),
        ):
            result = Plugin.list_installed("source")
        assert result[0]["enabled"] is False
        assert result[0]["added_at"] == "2026-01-01"


# ---------------------------------------------------------------------------
# Plugin.install
# ---------------------------------------------------------------------------


class TestInstallPlugin:
    def test_install_success(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.sources._load_plugin_fresh", return_value=None),
            patch("app.api.sources._clear_caches"),
        ):
            ok, message = Plugin.install("source", "garmin", skip_verify=True)
        assert ok is True
        assert "Garmin" in message

    def test_install_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Resolution failed")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=None),
        ):
            ok, message = Plugin.install("source", "nonexistent", skip_verify=True)
        assert ok is False
        assert "Resolution failed" in message

    def test_install_internal_blocked(self) -> None:
        with patch("app.api.sources._load_plugin", return_value=_InternalPluginCls):
            ok, message = Plugin.install("source", "internal", skip_verify=True)
        assert ok is False
        assert "internal plugin" in message

    def test_install_core_blocked(self) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            ok, message = Plugin.install("source", "core", skip_verify=True)
        assert ok is False
        assert "internal plugin" in message

    def test_install_verify_no_key(self, tmp_path: Path) -> None:
        with (
            patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", tmp_path / "missing.pub"),
            patch("app.api.sources._load_plugin", return_value=None),
        ):
            ok, message = Plugin.install("source", "garmin")
        assert ok is False
        assert "Public key not found" in message

    def test_install_verify_fails(self, tmp_path: Path) -> None:
        key_path = tmp_path / "shenas.pub"
        key_path.write_text("placeholder")
        with (
            patch("shenas_plugins.core.plugin.PUBLIC_KEY_PATH", key_path),
            patch("app.api.sources._load_plugin", return_value=None),
            patch("shenas_plugins.core.plugin._load_public_key", return_value=MagicMock()),
            patch("shenas_plugins.core.plugin._verify_from_index", return_value="No signature found"),
        ):
            ok, message = Plugin.install("source", "garmin")
        assert ok is False
        assert "No signature found" in message


# ---------------------------------------------------------------------------
# Plugin.uninstall
# ---------------------------------------------------------------------------


class TestUninstallPlugin:
    def test_uninstall_success(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.sources._clear_caches"),
        ):
            ok, message = Plugin.uninstall("source", "garmin")
        assert ok is True
        assert "Garmin" in message

    def test_uninstall_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Not installed")
        with (
            patch("shenas_plugins.core.plugin.subprocess.run", return_value=proc),
            patch("shenas_plugins.core.plugin._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._load_plugin", return_value=None),
        ):
            ok, message = Plugin.uninstall("source", "nonexistent")
        assert ok is False
        assert "Not installed" in message

    def test_uninstall_internal_blocked(self) -> None:
        with patch("app.api.sources._load_plugin", return_value=_InternalPluginCls):
            ok, message = Plugin.uninstall("source", "internal")
        assert ok is False
        assert "internal plugin" in message

    def test_uninstall_core_blocked(self) -> None:
        with patch("app.api.sources._load_plugin", return_value=None):
            ok, message = Plugin.uninstall("source", "core")
        assert ok is False
        assert "internal plugin" in message


# ---------------------------------------------------------------------------
# Streaming endpoints
# ---------------------------------------------------------------------------


class TestInstallStream:
    def test_install_stream_internal_blocked(self) -> None:
        with patch("app.api.sources._load_plugin", return_value=_InternalPluginCls):
            resp = client.post(
                "/api/plugins/source/install-stream",
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
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.sources._load_plugin_fresh", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._clear_caches"),
        ):
            resp = client.post(
                "/api/plugins/source/install-stream",
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
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
        ):
            resp = client.post(
                "/api/plugins/source/install-stream",
                json={"names": ["nonexistent"], "skip_verify": True},
            )
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert done[0]["ok"] is False

    def test_install_stream_no_name(self) -> None:
        resp = client.post("/api/plugins/source/install-stream", json={"names": []})
        assert resp.status_code == 400

    def test_install_stream_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/bogus/install-stream", json={"names": ["test"]})
        assert resp.status_code == 400


class TestRemoveStream:
    def test_remove_stream_internal_blocked(self) -> None:
        with patch("app.api.sources._load_plugin", return_value=_InternalPluginCls):
            resp = client.post("/api/plugins/source/internal/remove-stream")
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert len(done) == 1
        assert done[0]["ok"] is False

    def test_remove_stream_success(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="Uninstalled\n")
        with (
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
            patch("app.api.sources._clear_caches"),
        ):
            resp = client.post("/api/plugins/source/garmin/remove-stream")
        assert resp.status_code == 200
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert done[0]["ok"] is True

    def test_remove_stream_failure(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Not found\n")
        with (
            patch("app.api.sources._load_plugin", return_value=None),
            patch("app.api.plugins._run_subprocess", return_value=proc),
            patch("app.api.plugins._python_executable", return_value="/usr/bin/python3"),
        ):
            resp = client.post("/api/plugins/source/garmin/remove-stream")
        events = parse_sse(resp.text)
        done = [e for e in events if e.get("event") == "done"]
        assert done[0]["ok"] is False

    def test_remove_stream_invalid_kind(self) -> None:
        resp = client.post("/api/plugins/bogus/garmin/remove-stream")
        assert resp.status_code == 400
