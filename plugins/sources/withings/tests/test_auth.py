import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.withings.source import WithingsSource


@pytest.fixture
def pipe() -> WithingsSource:
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
    def test_no_tokens_raises(self, pipe: WithingsSource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No Withings tokens"):
            pipe.build_client()

    def test_empty_tokens_raises(self, pipe: WithingsSource, auth_mock) -> None:
        auth_mock.read.return_value = {"tokens": None}
        with pytest.raises(RuntimeError, match="No Withings tokens"):
            pipe.build_client()

    @patch("shenas_sources.withings.client.WithingsClient")
    def test_valid_tokens_returns_client(self, mock_cls: MagicMock, pipe: WithingsSource, auth_mock) -> None:
        import time

        tokens = {
            "access_token": "abc",
            "refresh_token": "def",
            "expires_at": time.time() + 3600,
            "client_id": "cid",
            "client_secret": "csec",
        }
        auth_mock.read.return_value = {"tokens": json.dumps(tokens)}
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        result = pipe.build_client()

        assert result is mock_client
        mock_cls.assert_called_once_with("abc")

    @patch("shenas_sources.withings.client.WithingsClient")
    def test_expired_tokens_refreshes(self, mock_cls: MagicMock, pipe: WithingsSource, auth_mock) -> None:
        tokens = {
            "access_token": "old",
            "refresh_token": "ref",
            "expires_at": 0,
            "client_id": "cid",
            "client_secret": "csec",
        }
        auth_mock.read.return_value = {"tokens": json.dumps(tokens)}
        mock_cls.refresh_tokens.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 10800,
        }
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        result = pipe.build_client()

        assert result is mock_client
        mock_cls.refresh_tokens.assert_called_once_with("cid", "csec", "ref")
        mock_cls.assert_called_once_with("new_access")
        auth_mock.write.assert_called_once()
        saved = json.loads(auth_mock.write.call_args.kwargs["tokens"])
        assert saved["access_token"] == "new_access"
        assert saved["refresh_token"] == "new_refresh"


class TestOAuth:
    def test_start_oauth_missing_credentials_raises(self, pipe: WithingsSource, auth_mock) -> None:
        with pytest.raises(ValueError, match="client_id and client_secret are required"):
            pipe.start_oauth("http://localhost/callback", credentials={"client_id": "", "client_secret": ""})

    def test_start_oauth_returns_url(self, pipe: WithingsSource, auth_mock) -> None:
        url = pipe.start_oauth(
            "http://localhost/callback",
            credentials={"client_id": "cid", "client_secret": "csec"},
        )
        assert "account.withings.com" in url
        assert "client_id=cid" in url

    def test_complete_oauth_no_pending_raises(self, pipe: WithingsSource, auth_mock) -> None:
        from shenas_sources.withings.source import _pending_oauth

        _pending_oauth.pop("withings", None)
        with pytest.raises(RuntimeError, match="No pending Withings OAuth flow"):
            pipe.complete_oauth(code="test_code")

    @patch("shenas_sources.withings.client.WithingsClient.exchange_code")
    def test_complete_oauth_stores_tokens(self, mock_exchange: MagicMock, pipe: WithingsSource, auth_mock) -> None:
        from shenas_sources.withings.source import _pending_oauth

        _pending_oauth["withings"] = {
            "client_id": "cid",
            "client_secret": "csec",
            "redirect_uri": "http://localhost/callback",
        }
        mock_exchange.return_value = {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 10800,
            "userid": "12345",
        }

        pipe.complete_oauth(code="test_code")

        mock_exchange.assert_called_once_with("cid", "csec", "test_code", "http://localhost/callback")
        auth_mock.write.assert_called_once()
        saved = json.loads(auth_mock.write.call_args.kwargs["tokens"])
        assert saved["access_token"] == "at"
        assert saved["client_id"] == "cid"
        assert saved["userid"] == "12345"
