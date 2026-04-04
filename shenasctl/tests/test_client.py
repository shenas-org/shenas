"""Tests for the ShenasClient HTTP client."""

from unittest.mock import MagicMock, patch

import pytest

from shenasctl.client import ShenasClient, ShenasServerError


class TestConnectionHandling:
    def test_default_url(self) -> None:
        client = ShenasClient()
        assert client.base_url == "https://localhost:7280"
        client.close()

    def test_custom_url(self) -> None:
        client = ShenasClient(base_url="https://example.com:9090")
        assert client.base_url == "https://example.com:9090"
        client.close()

    def test_env_var_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHENAS_SERVER_URL", "https://custom:1234")
        client = ShenasClient()
        assert client.base_url == "https://custom:1234"
        client.close()

    def test_explicit_url_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SHENAS_SERVER_URL", "https://from-env:1234")
        client = ShenasClient(base_url="https://explicit:5678")
        assert client.base_url == "https://explicit:5678"
        client.close()


class TestRequestErrorHandling:
    def test_connect_error_raises_friendly_message(self) -> None:
        client = ShenasClient(base_url="https://localhost:19999")
        with pytest.raises(ShenasServerError) as exc_info:
            client._request("GET", "/api/health")
        assert exc_info.value.status_code == 0
        assert "Cannot reach shenas server" in exc_info.value.detail
        client.close()

    def test_server_error_json_body(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "Not found"}
        mock_resp.text = "Not found"

        client = ShenasClient()
        with (
            patch.object(client._client, "request", return_value=mock_resp),
            pytest.raises(ShenasServerError) as exc_info,
        ):
            client._request("GET", "/api/missing")
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"
        client.close()

    def test_server_error_plain_text(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "Internal Server Error"

        client = ShenasClient()
        with (
            patch.object(client._client, "request", return_value=mock_resp),
            pytest.raises(ShenasServerError) as exc_info,
        ):
            client._request("GET", "/api/broken")
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal Server Error"
        client.close()


class TestIsServerRunning:
    def test_running(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client = ShenasClient()
        with patch.object(client._client, "get", return_value=mock_resp):
            assert client.is_server_running() is True
        client.close()

    def test_not_running(self) -> None:
        client = ShenasClient(base_url="https://localhost:19999")
        assert client.is_server_running() is False
        client.close()


class TestSSEParsing:
    def test_parses_events(self) -> None:
        lines = [
            "event: progress",
            'data: {"pipe": "garmin", "message": "starting"}',
            "",
            "event: complete",
            'data: {"pipe": "garmin", "message": "done"}',
        ]

        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(lines)

        client = ShenasClient()
        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client._stream_sse("POST", "/api/sync"))

        assert len(events) == 2
        assert events[0]["_event"] == "progress"
        assert events[0]["pipe"] == "garmin"
        assert events[1]["_event"] == "complete"
        assert events[1]["message"] == "done"
        client.close()

    def test_resets_event_type_after_yield(self) -> None:
        lines = [
            "event: error",
            'data: {"message": "failed"}',
            "",
            'data: {"message": "no event field"}',
        ]

        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = iter(lines)

        client = ShenasClient()
        with patch.object(client._client, "stream", return_value=mock_resp):
            events = list(client._stream_sse("POST", "/api/sync"))

        assert events[0]["_event"] == "error"
        assert events[1]["_event"] == "message"
        client.close()

    def test_connect_error(self) -> None:
        client = ShenasClient(base_url="https://localhost:19999")
        with pytest.raises(ShenasServerError) as exc_info:
            list(client.sync_all())
        assert "Cannot reach shenas server" in exc_info.value.detail
        client.close()
