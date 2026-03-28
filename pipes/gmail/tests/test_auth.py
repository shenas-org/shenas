from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.gmail.auth import build_client


class TestBuildClient:
    def test_no_credentials_raises(self) -> None:
        with patch("shenas_pipes.gmail.auth._get_stored_token", return_value=None):
            with pytest.raises(RuntimeError, match="No valid Gmail credentials"):
                build_client()

    @patch("shenas_pipes.gmail.auth.build")
    def test_valid_token(self, mock_build: MagicMock) -> None:
        mock_creds = MagicMock()
        mock_creds.valid = True
        with patch("shenas_pipes.gmail.auth._get_stored_token", return_value=mock_creds):
            build_client()
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

    @patch("shenas_pipes.gmail.auth.build")
    @patch("shenas_pipes.gmail.auth._store_token")
    def test_expired_token_refreshes(self, mock_store: MagicMock, mock_build: MagicMock) -> None:
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh123"
        with patch("shenas_pipes.gmail.auth._get_stored_token", return_value=mock_creds):
            build_client()
        mock_creds.refresh.assert_called_once()
        mock_store.assert_called_once_with(mock_creds)
