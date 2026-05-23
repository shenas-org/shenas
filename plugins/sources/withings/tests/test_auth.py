import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.withings.source import WithingsSource

_TEST_CREDS = {
    "SHENAS_WITHINGS_CLIENT_ID": "test-client-id",
    "SHENAS_WITHINGS_CLIENT_SECRET": "test-client-secret",
}


@pytest.fixture
def source() -> WithingsSource:
    return WithingsSource.__new__(WithingsSource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(WithingsSource.Auth, "read_row") as read,
        patch.object(WithingsSource.Auth, "write_row") as write,
        patch.object(WithingsSource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    def test_no_tokens_raises(self, source: WithingsSource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No Withings tokens"):
            source.build_client()

    def test_empty_tokens_raises(self, source: WithingsSource, auth_mock) -> None:
        auth_mock.read.return_value = {"tokens": None}
        with pytest.raises(RuntimeError, match="No Withings tokens"):
            source.build_client()

    @patch("shenas_sources.withings.client.WithingsClient")
    def test_valid_tokens_returns_client(self, mock_cls: MagicMock, source: WithingsSource, auth_mock) -> None:
        import time

        tokens = {
            "access_token": "abc",
            "refresh_token": "def",
            "expires_at": time.time() + 3600,
        }
        auth_mock.read.return_value = {"tokens": json.dumps(tokens)}
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        result = source.build_client()

        assert result is mock_client
        mock_cls.assert_called_once_with("abc")

    @patch("shenas_sources.withings.client.WithingsClient")
    def test_expired_tokens_refreshes(self, mock_cls: MagicMock, source: WithingsSource, auth_mock) -> None:
        tokens = {
            "access_token": "old",
            "refresh_token": "ref",
            "expires_at": 0,
        }
        auth_mock.read.return_value = {"tokens": json.dumps(tokens)}
        mock_cls.refresh_tokens.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 10800,
        }
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        with patch.dict(os.environ, _TEST_CREDS):
            result = source.build_client()

        assert result is mock_client
        mock_cls.assert_called_once_with("new_access")
        auth_mock.write.assert_called_once()
        saved = json.loads(auth_mock.write.call_args.kwargs["tokens"])
        assert saved["access_token"] == "new_access"
        assert saved["refresh_token"] == "new_refresh"


class TestCredentials:
    def test_missing_env_vars_raises(self, source: WithingsSource, auth_mock) -> None:
        for key in ("SHENAS_WITHINGS_CLIENT_ID", "SHENAS_WITHINGS_CLIENT_SECRET"):
            os.environ.pop(key, None)
        tokens = {"access_token": "a", "refresh_token": "b", "expires_at": 0}
        auth_mock.read.return_value = {"tokens": json.dumps(tokens)}
        with (
            patch("shenas_sources.withings.client.WithingsClient"),
            pytest.raises(RuntimeError, match="SHENAS_WITHINGS_CLIENT_SECRET"),
        ):
            source.build_client()


class TestOAuth:
    def test_start_oauth_returns_url(self, source: WithingsSource, auth_mock) -> None:
        with patch.dict(os.environ, _TEST_CREDS):
            url = source.start_oauth("http://localhost/callback")
        assert "account.withings.com" in url

    def test_complete_oauth_no_pending_raises(self, source: WithingsSource, auth_mock) -> None:
        from shenas_sources.withings.source import _pending_oauth

        _pending_oauth.pop("withings", None)
        with pytest.raises(RuntimeError, match="No pending Withings OAuth flow"):
            source.complete_oauth(code="test_code")

    @patch("shenas_sources.withings.client.WithingsClient.exchange_code")
    def test_complete_oauth_stores_tokens(self, mock_exchange: MagicMock, source: WithingsSource, auth_mock) -> None:
        from shenas_sources.withings.source import _pending_oauth

        _pending_oauth["withings"] = {"redirect_uri": "http://localhost/callback"}
        mock_exchange.return_value = {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 10800,
            "userid": "12345",
        }

        with patch.dict(os.environ, _TEST_CREDS):
            source.complete_oauth(code="test_code")

        auth_mock.write.assert_called_once()
        saved = json.loads(auth_mock.write.call_args.kwargs["tokens"])
        assert saved["access_token"] == "at"
        assert saved["userid"] == "12345"
