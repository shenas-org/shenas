from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.garmin.source import GarminSource


@pytest.fixture
def source() -> GarminSource:
    return GarminSource.__new__(GarminSource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(GarminSource.Auth, "read_row") as read,
        patch.object(GarminSource.Auth, "write_row") as write,
        patch.object(GarminSource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    def test_no_tokens_raises(self, source: GarminSource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No valid tokens"):
            source.build_client()

    def test_empty_tokens_raises(self, source: GarminSource, auth_mock) -> None:
        auth_mock.read.return_value = {"tokens": None}
        with pytest.raises(RuntimeError, match="No valid tokens"):
            source.build_client()

    @patch("garminconnect.Garmin")
    def test_valid_tokens_login_success(self, mock_garmin_cls: MagicMock, source: GarminSource, auth_mock) -> None:
        fake_tokens = '{"oauth1_token.json": "{\\"token\\": \\"a\\"}", "oauth2_token.json": "{\\"token\\": \\"b\\"}"}'
        auth_mock.read.return_value = {"tokens": fake_tokens}

        mock_client = MagicMock()
        mock_garmin_cls.return_value = mock_client

        result = source.build_client()

        assert result is mock_client
        mock_client.login.assert_called_once()

    @patch("garminconnect.Garmin")
    def test_login_fails_raises(self, mock_garmin_cls: MagicMock, source: GarminSource, auth_mock) -> None:
        fake_tokens = '{"oauth1_token.json": "{\\"token\\": \\"stale\\"}"}'
        auth_mock.read.return_value = {"tokens": fake_tokens}

        mock_client = MagicMock()
        mock_client.login.side_effect = Exception("expired")
        mock_garmin_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="No valid tokens"):
            source.build_client()
