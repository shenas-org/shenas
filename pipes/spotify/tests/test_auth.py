from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.spotify.auth import authenticate, build_client

MODULE = "shenas_pipes.spotify.auth"


class TestBuildClient:
    def test_no_tokens_raises(self) -> None:
        with patch(f"{MODULE}._get_stored_tokens", return_value=None):
            with pytest.raises(RuntimeError, match="No Spotify tokens"):
                build_client()

    @patch(f"{MODULE}.SpotifyOAuth")
    @patch(f"{MODULE}.spotipy.Spotify")
    def test_returns_client(self, mock_spotify: MagicMock, mock_oauth_cls: MagicMock) -> None:
        tokens = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": 9999999999,
            "client_id": "cid",
            "client_secret": "sec",
        }
        mock_oauth = MagicMock()
        mock_oauth.is_token_expired.return_value = False
        mock_oauth_cls.return_value = mock_oauth

        with patch(f"{MODULE}._get_stored_tokens", return_value=tokens):
            build_client()

        mock_spotify.assert_called_once_with(auth="tok")


class TestAuthenticate:
    def test_missing_credentials(self) -> None:
        with pytest.raises(ValueError, match="client_id and client_secret"):
            authenticate({})

    @patch(f"{MODULE}.SpotifyOAuth")
    def test_raises_oauth_url(self, mock_oauth_cls: MagicMock) -> None:
        mock_oauth = MagicMock()
        mock_oauth.get_authorize_url.return_value = "https://accounts.spotify.com/authorize?foo=bar"
        mock_oauth_cls.return_value = mock_oauth

        with pytest.raises(ValueError, match="OAUTH_URL:https://accounts.spotify.com/authorize"):
            authenticate({"client_id": "cid", "client_secret": "sec"})
