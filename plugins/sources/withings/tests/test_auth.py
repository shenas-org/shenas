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


class TestAuthenticate:
    def test_missing_credentials_raises(self, pipe: WithingsSource, auth_mock) -> None:
        with pytest.raises(ValueError, match="client_id and client_secret are required"):
            pipe.authenticate({"client_id": "", "client_secret": ""})

    def test_initial_auth_raises_oauth_url(self, pipe: WithingsSource, auth_mock) -> None:
        with pytest.raises(ValueError, match="OAUTH_URL:"):
            pipe.authenticate({"client_id": "cid", "client_secret": "csec"})

    def test_auth_complete_no_pending_raises(self, pipe: WithingsSource, auth_mock) -> None:
        from shenas_sources.withings.source import _pending_auth

        _pending_auth.pop("withings", None)  # clear any leftover from prior test
        with pytest.raises(ValueError, match="No pending auth flow"):
            pipe.authenticate({"auth_complete": "true"})
