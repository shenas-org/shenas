from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.duolingo.pipe import DuolingoPipe


@pytest.fixture
def pipe() -> DuolingoPipe:
    p = DuolingoPipe.__new__(DuolingoPipe)
    p._auth_store = MagicMock()
    p._config_store = MagicMock()
    return p


class TestBuildClient:
    def test_no_jwt_raises(self, pipe: DuolingoPipe) -> None:
        pipe._auth_store.get.return_value = None
        with pytest.raises(RuntimeError, match="No JWT token"):
            pipe.build_client()

    @patch("shenas_pipes.duolingo.client.DuolingoClient")
    def test_returns_client_with_jwt(self, mock_cls: MagicMock, pipe: DuolingoPipe) -> None:
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjYzMDcyMDAwMDAsImlhdCI6MCwic3ViIjoxMjM0NX0.X"
        pipe._auth_store.get.return_value = {"jwt_token": jwt}

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        client = pipe.build_client()

        mock_cls.assert_called_once_with(jwt)
        assert client is mock_client


class TestAuthenticate:
    def test_missing_token(self, pipe: DuolingoPipe) -> None:
        with pytest.raises(ValueError, match="jwt_token is required"):
            pipe.authenticate({})

    @patch("shenas_pipes.duolingo.client.DuolingoClient")
    def test_success(self, mock_cls: MagicMock, pipe: DuolingoPipe) -> None:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        pipe.authenticate({"jwt_token": "tok-123"})

        mock_cls.assert_called_once_with("tok-123")
        pipe._auth_store.set.assert_called_once_with(DuolingoPipe.Auth, jwt_token="tok-123")
        mock_client.get_user.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("shenas_pipes.duolingo.client.DuolingoClient")
    def test_invalid_token(self, mock_cls: MagicMock, pipe: DuolingoPipe) -> None:
        mock_client = MagicMock()
        mock_client.get_user.side_effect = Exception("401 Unauthorized")
        mock_cls.return_value = mock_client

        with pytest.raises(Exception, match="401"):
            pipe.authenticate({"jwt_token": "bad-token"})
        mock_client.close.assert_called_once()
