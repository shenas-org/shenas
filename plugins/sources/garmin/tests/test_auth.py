from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.garmin.pipe import GarminSource


@pytest.fixture
def pipe() -> GarminSource:
    p = GarminSource.__new__(GarminSource)
    p._auth_store = MagicMock()
    p._config_store = MagicMock()
    return p


class TestBuildClient:
    def test_no_tokens_raises(self, pipe: GarminSource) -> None:
        pipe._auth_store.get.return_value = None
        with pytest.raises(RuntimeError, match="No valid tokens"):
            pipe.build_client()

    def test_empty_tokens_raises(self, pipe: GarminSource) -> None:
        pipe._auth_store.get.return_value = {"tokens": None}
        with pytest.raises(RuntimeError, match="No valid tokens"):
            pipe.build_client()

    @patch("garminconnect.Garmin")
    def test_valid_tokens_login_success(self, mock_garmin_cls: MagicMock, pipe: GarminSource) -> None:
        fake_tokens = '{"oauth1_token.json": "{\\"token\\": \\"a\\"}", "oauth2_token.json": "{\\"token\\": \\"b\\"}"}'
        pipe._auth_store.get.return_value = {"tokens": fake_tokens}

        mock_client = MagicMock()
        mock_garmin_cls.return_value = mock_client

        result = pipe.build_client()

        assert result is mock_client
        mock_client.login.assert_called_once()

    @patch("garminconnect.Garmin")
    def test_login_fails_raises(self, mock_garmin_cls: MagicMock, pipe: GarminSource) -> None:
        fake_tokens = '{"oauth1_token.json": "{\\"token\\": \\"stale\\"}"}'
        pipe._auth_store.get.return_value = {"tokens": fake_tokens}

        mock_client = MagicMock()
        mock_client.login.side_effect = Exception("expired")
        mock_garmin_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="No valid tokens"):
            pipe.build_client()
