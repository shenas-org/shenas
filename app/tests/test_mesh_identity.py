"""Tests for app.mesh.identity -- device keypair generation, info, registration."""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from app.mesh import identity


class TestDetectDeviceType:
    @pytest.mark.parametrize(
        ("system", "expected"),
        [
            ("Android", "mobile"),
            ("Darwin", "desktop"),
            ("Linux", "desktop"),
            ("Windows", "desktop"),
            ("FreeBSD", "unknown"),
        ],
    )
    def test_each_system(self, system: str, expected: str) -> None:
        with patch("app.mesh.identity.platform.system", return_value=system):
            assert identity._detect_device_type() == expected


class TestRandomDeviceName:
    def test_format(self) -> None:
        name = identity._random_device_name()
        assert re.fullmatch(r"[a-z]+-[a-z]+-\d{2}", name), f"unexpected format: {name}"

    def test_not_hostname(self) -> None:
        import socket

        hostname = socket.gethostname()
        names = {identity._random_device_name() for _ in range(20)}
        assert hostname not in names


class TestGetOrCreateIdentity:
    def test_creates_non_pii_name(self, patch_db: None) -> None:
        first = identity._get_or_create_identity()
        assert first["device_name"]
        import socket

        assert first["device_name"] != socket.gethostname()
        assert re.fullmatch(r"[a-z]+-[a-z]+-\d{2}", first["device_name"]), (
            f"default name is not non-PII: {first['device_name']}"
        )

    def test_creates_then_reuses(self, patch_db: None) -> None:
        first = identity._get_or_create_identity()
        assert "BEGIN PRIVATE KEY" in first["private_key"]
        assert "BEGIN PUBLIC KEY" in first["public_key"]

        second = identity._get_or_create_identity()
        assert second["private_key"] == first["private_key"]
        assert second["public_key"] == first["public_key"]
        assert second["device_name"] == first["device_name"]

    def test_hostname_never_stored(self, patch_db: None) -> None:
        import platform
        import socket

        hostname = socket.gethostname()
        node_name = platform.node()
        identity._get_or_create_identity()
        stored = identity.DeviceIdentity.get("device_name")
        assert stored != hostname
        assert stored != node_name


class TestGetDeviceInfo:
    def test_returns_public_fields_only(self, patch_db: None) -> None:
        info = identity.get_device_info()
        assert set(info.keys()) == {"device_name", "public_key", "device_type"}
        assert "private_key" not in info
        assert info["device_type"] in {"desktop", "mobile", "unknown"}


class TestRenameDevice:
    def test_updates_local_store(self, patch_db: None) -> None:
        identity._get_or_create_identity()
        identity.rename_device("my-laptop")
        assert identity.DeviceIdentity.get("device_name") == "my-laptop"

    def test_propagates_to_server_when_registered(self, patch_db: None) -> None:
        identity._get_or_create_identity()
        identity.DeviceIdentity.put("server_device_id", "srv-dev-1")

        mock_resp = MagicMock(status_code=200, json=lambda: {"id": "srv-dev-1", "name": "new-name"})
        with patch("httpx.patch", return_value=mock_resp) as mock_patch:
            identity.rename_device("new-name", server_url="https://example.com", token="tok")

        mock_patch.assert_called_once()
        call = mock_patch.call_args
        assert call.args[0] == "https://example.com/api/devices/srv-dev-1"
        assert call.kwargs["json"] == {"name": "new-name"}
        assert call.kwargs["headers"] == {"Authorization": "Bearer tok"}

    def test_skips_server_when_not_registered(self, patch_db: None) -> None:
        identity._get_or_create_identity()
        # No server_device_id stored

        with patch("httpx.patch") as mock_patch:
            identity.rename_device("new-name", server_url="https://example.com", token="tok")

        mock_patch.assert_not_called()
        assert identity.DeviceIdentity.get("device_name") == "new-name"

    def test_skips_server_when_no_credentials(self, patch_db: None) -> None:
        identity._get_or_create_identity()
        identity.DeviceIdentity.put("server_device_id", "srv-dev-1")

        with patch("httpx.patch") as mock_patch:
            identity.rename_device("offline-name")

        mock_patch.assert_not_called()
        assert identity.DeviceIdentity.get("device_name") == "offline-name"


class TestRegisterWithServer:
    def test_sends_non_pii_name_not_hostname(self, patch_db: None) -> None:
        """Hostname must never reach the server; default is always non-PII."""
        import socket

        mock_resp = MagicMock(status_code=200, json=lambda: {"id": "dev-1"})
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            identity.register_with_server("https://example.com", "tok")

        sent_name = mock_post.call_args.kwargs["json"]["name"]
        assert sent_name != socket.gethostname(), "hostname must not reach the server"
        assert re.fullmatch(r"[a-z]+-[a-z]+-\d{2}", sent_name), f"expected non-PII default but got: {sent_name}"

    def test_success(self, patch_db: None) -> None:
        mock_resp = MagicMock(status_code=200, json=lambda: {"id": "dev-1"})
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            result = identity.register_with_server("https://example.com", "tok")
        assert result == {"id": "dev-1"}
        mock_post.assert_called_once()
        call = mock_post.call_args
        assert call.args[0] == "https://example.com/api/devices"
        assert call.kwargs["headers"] == {"Authorization": "Bearer tok"}
        assert "name" in call.kwargs["json"]
        assert "public_key" in call.kwargs["json"]

    def test_non_200_returns_none(self, patch_db: None) -> None:
        mock_resp = MagicMock(status_code=403, text="forbidden")
        with patch("httpx.post", return_value=mock_resp):
            assert identity.register_with_server("https://example.com", "tok") is None

    def test_network_error_returns_none(self, patch_db: None) -> None:
        with patch("httpx.post", side_effect=RuntimeError("boom")):
            assert identity.register_with_server("https://example.com", "tok") is None

    def test_custom_name_sent_after_rename(self, patch_db: None) -> None:
        """After rename_device, the server receives the user-chosen name."""
        identity._get_or_create_identity()
        identity.rename_device("alex-work-laptop")

        mock_resp = MagicMock(status_code=200, json=lambda: {"id": "dev-1"})
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            identity.register_with_server("https://example.com", "tok")

        sent_name = mock_post.call_args.kwargs["json"]["name"]
        assert sent_name == "alex-work-laptop"
