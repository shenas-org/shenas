from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.garmin.auth import build_client


class TestBuildClient:
    def test_no_tokens_no_credentials_raises(self) -> None:
        with patch("shenas_pipes.garmin.auth._get_stored_tokens", return_value=None):
            with pytest.raises(RuntimeError, match="No valid tokens"):
                build_client()

    @patch("shenas_pipes.garmin.auth.Garmin")
    def test_keyring_login_success(self, mock_garmin_cls: MagicMock) -> None:
        fake_tokens = {"oauth1_token.json": '{"token": "a"}', "oauth2_token.json": '{"token": "b"}'}
        mock_client = MagicMock()
        mock_garmin_cls.return_value = mock_client

        with patch("shenas_pipes.garmin.auth._get_stored_tokens", return_value=fake_tokens):
            result = build_client()

        assert result is mock_client
        mock_client.login.assert_called_once()

    @patch("shenas_pipes.garmin.auth.Garmin")
    def test_keyring_login_fails_falls_back(self, mock_garmin_cls: MagicMock) -> None:
        fake_tokens = {"oauth1_token.json": '{"token": "stale"}'}

        keyring_client = MagicMock()
        keyring_client.login.side_effect = Exception("expired")

        cred_client = MagicMock()
        cred_client.garth = MagicMock()

        mock_garmin_cls.side_effect = [keyring_client, cred_client]

        with (
            patch("shenas_pipes.garmin.auth._get_stored_tokens", return_value=fake_tokens),
            patch("shenas_pipes.garmin.auth._store_tokens"),
        ):
            result = build_client(email="a@b.com", password="pass")

        assert result is cred_client
