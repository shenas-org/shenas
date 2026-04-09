from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.tile.source import TileSource


@pytest.fixture
def pipe() -> TileSource:
    return TileSource.__new__(TileSource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(TileSource.Auth, "read_row") as read,
        patch.object(TileSource.Auth, "write_row") as write,
        patch.object(TileSource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    def test_no_tokens_raises(self, pipe: TileSource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No credentials found"):
            pipe.build_client()

    def test_empty_tokens_raises(self, pipe: TileSource, auth_mock) -> None:
        auth_mock.read.return_value = {"tokens": None}
        with pytest.raises(RuntimeError, match="No credentials found"):
            pipe.build_client()

    @patch("shenas_sources.tile.client.TileClient")
    def test_valid_tokens_login_success(self, mock_tile_cls: MagicMock, pipe: TileSource, auth_mock) -> None:
        import json

        creds = json.dumps({"email": "test@example.com", "password": "secret", "client_uuid": "abc-123"})
        auth_mock.read.return_value = {"tokens": creds}

        mock_client = MagicMock()
        mock_tile_cls.return_value = mock_client

        result = pipe.build_client()

        assert result is mock_client
        mock_client.login.assert_called_once()
        mock_tile_cls.assert_called_once_with("test@example.com", "secret", client_uuid="abc-123")


class TestAuthenticate:
    def test_missing_email_raises(self, pipe: TileSource, auth_mock) -> None:
        with pytest.raises(ValueError, match="email and password are required"):
            pipe.authenticate({"email": "", "password": "secret"})

    def test_missing_password_raises(self, pipe: TileSource, auth_mock) -> None:
        with pytest.raises(ValueError, match="email and password are required"):
            pipe.authenticate({"email": "test@example.com", "password": ""})

    @patch("shenas_sources.tile.client.TileClient")
    def test_successful_auth_stores_tokens(self, mock_tile_cls: MagicMock, pipe: TileSource, auth_mock) -> None:
        import json

        mock_client = MagicMock()
        mock_client.client_uuid = "gen-uuid"
        mock_tile_cls.return_value = mock_client

        pipe.authenticate({"email": "test@example.com", "password": "secret"})

        mock_client.login.assert_called_once()
        mock_client.close.assert_called_once()
        auth_mock.write.assert_called_once()
        stored = json.loads(auth_mock.write.call_args.kwargs["tokens"])
        assert stored["email"] == "test@example.com"
        assert stored["password"] == "secret"
        assert stored["client_uuid"] == "gen-uuid"
