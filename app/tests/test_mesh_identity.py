"""Tests for app.mesh.identity -- device keypair generation, info, registration."""

from __future__ import annotations

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


class TestGetOrCreateIdentity:
    def test_creates_then_reuses(self, patch_db: None) -> None:
        first = identity._get_or_create_identity()
        assert first["device_name"]
        assert "BEGIN PRIVATE KEY" in first["private_key"]
        assert "BEGIN PUBLIC KEY" in first["public_key"]

        second = identity._get_or_create_identity()
        assert second["private_key"] == first["private_key"]
        assert second["public_key"] == first["public_key"]
        assert second["device_name"] == first["device_name"]


class TestGetDeviceInfo:
    def test_returns_public_fields_only(self, patch_db: None) -> None:
        info = identity.get_device_info()
        assert set(info.keys()) == {"device_name", "public_key", "device_type"}
        assert "private_key" not in info
        assert info["device_type"] in {"desktop", "mobile", "unknown"}


class TestRegisterWithServer:
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
