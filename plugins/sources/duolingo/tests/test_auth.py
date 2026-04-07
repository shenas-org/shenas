from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.duolingo.source import DuolingoSource


@pytest.fixture
def pipe() -> DuolingoSource:
    return DuolingoSource.__new__(DuolingoSource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(DuolingoSource.Auth, "read_row") as read,
        patch.object(DuolingoSource.Auth, "write_row") as write,
        patch.object(DuolingoSource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    def test_no_jwt_raises(self, pipe: DuolingoSource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No JWT token"):
            pipe.build_client()

    @patch("shenas_sources.duolingo.client.DuolingoClient")
    def test_returns_client_with_jwt(self, mock_cls: MagicMock, pipe: DuolingoSource, auth_mock) -> None:
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjYzMDcyMDAwMDAsImlhdCI6MCwic3ViIjoxMjM0NX0.X"
        auth_mock.read.return_value = {"jwt_token": jwt}

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        client = pipe.build_client()

        mock_cls.assert_called_once_with(jwt)
        assert client is mock_client


class TestAuthenticate:
    def test_missing_token(self, pipe: DuolingoSource) -> None:
        with pytest.raises(ValueError, match="jwt_token is required"):
            pipe.authenticate({})

    @patch("shenas_sources.duolingo.client.DuolingoClient")
    def test_success(self, mock_cls: MagicMock, pipe: DuolingoSource, auth_mock) -> None:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        pipe.authenticate({"jwt_token": "tok-123"})

        mock_cls.assert_called_once_with("tok-123")
        auth_mock.write.assert_called_once_with(jwt_token="tok-123")
        mock_client.get_user.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("shenas_sources.duolingo.client.DuolingoClient")
    def test_invalid_token(self, mock_cls: MagicMock, pipe: DuolingoSource) -> None:
        mock_client = MagicMock()
        mock_client.get_user.side_effect = Exception("401 Unauthorized")
        mock_cls.return_value = mock_client

        with pytest.raises(Exception, match="401"):
            pipe.authenticate({"jwt_token": "bad-token"})
        mock_client.close.assert_called_once()
