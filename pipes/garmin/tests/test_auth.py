from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.garmin.auth import build_client


class TestBuildClient:
    def test_no_tokens_no_credentials_raises(self, tmp_path: Path) -> None:
        token_store = str(tmp_path / "tokens")
        with pytest.raises(RuntimeError, match="No valid tokens"):
            build_client(token_store=token_store)

    def test_empty_token_dir_no_credentials_raises(self, tmp_path: Path) -> None:
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        with pytest.raises(RuntimeError, match="No valid tokens"):
            build_client(token_store=str(token_dir))

    @patch("shenas_pipes.garmin.auth.Garmin")
    def test_token_login_success(self, mock_garmin_cls: MagicMock, tmp_path: Path) -> None:
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        (token_dir / "oauth_token").write_text("fake")

        mock_client = MagicMock()
        mock_garmin_cls.return_value = mock_client

        result = build_client(token_store=str(token_dir))
        assert result is mock_client
        mock_client.login.assert_called_once_with(str(token_dir))

    @patch("shenas_pipes.garmin.auth.Garmin")
    def test_token_login_fails_falls_back_to_credentials(self, mock_garmin_cls: MagicMock, tmp_path: Path) -> None:
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        (token_dir / "oauth_token").write_text("stale")

        token_client = MagicMock()
        token_client.login.side_effect = Exception("expired")

        cred_client = MagicMock()

        mock_garmin_cls.side_effect = [token_client, cred_client]

        result = build_client(email="a@b.com", password="pass", token_store=str(token_dir))
        assert result is cred_client
