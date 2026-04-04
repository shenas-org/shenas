from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.gmail.auth import _auth, build_client


class TestBuildClient:
    def test_no_credentials_raises(self) -> None:
        with (
            patch.object(_auth, "_get_stored_token", return_value=None),
            pytest.raises(RuntimeError, match="No valid credentials"),
        ):
            build_client()

    @patch("shenas_pipes.core.google_auth.build")
    def test_valid_token(self, mock_build: MagicMock) -> None:
        mock_creds = MagicMock()
        mock_creds.valid = True
        with patch.object(_auth, "_get_stored_token", return_value=mock_creds):
            build_client()
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds, static_discovery=True)

    @patch("shenas_pipes.core.google_auth.build")
    def test_expired_token_refreshes(self, mock_build: MagicMock) -> None:
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh123"
        with (
            patch.object(_auth, "_get_stored_token", return_value=mock_creds),
            patch.object(_auth, "_store_token") as mock_store,
        ):
            build_client()
        mock_creds.refresh.assert_called_once()
        mock_store.assert_called_once_with(mock_creds)
