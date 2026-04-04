from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.spotify.auth import authenticate, build_client

MODULE = "shenas_pipes.spotify.auth"


class TestBuildClient:
    def test_no_tokens_raises(self) -> None:
        with (
            patch(f"{MODULE}._get_stored_tokens", return_value=None),
            pytest.raises(RuntimeError, match="No Spotify tokens"),
        ):
            build_client()

    @patch(f"{MODULE}.SpotifyPKCE")
    @patch(f"{MODULE}.spotipy.Spotify")
    def test_returns_client(self, mock_spotify: MagicMock, mock_pkce_cls: MagicMock) -> None:
        tokens = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": 9999999999,
            "client_id": "cid",
        }
        mock_pkce = MagicMock()
        mock_pkce.is_token_expired.return_value = False
        mock_pkce_cls.return_value = mock_pkce

        with patch(f"{MODULE}._get_stored_tokens", return_value=tokens):
            build_client()

        mock_spotify.assert_called_once_with(auth="tok")


class TestAuthenticate:
    def test_missing_credentials(self) -> None:
        with pytest.raises(ValueError, match="client_id is required"):
            authenticate({})

    @patch(f"{MODULE}.SpotifyPKCE")
    def test_raises_oauth_url(self, mock_pkce_cls: MagicMock) -> None:
        mock_pkce = MagicMock()
        mock_pkce.get_authorize_url.return_value = "https://accounts.spotify.com/authorize?foo=bar"
        mock_pkce_cls.return_value = mock_pkce

        with pytest.raises(ValueError, match=r"OAUTH_URL:https://accounts.spotify.com/authorize"):
            authenticate({"client_id": "cid"})
