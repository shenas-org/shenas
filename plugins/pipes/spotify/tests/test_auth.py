from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# The pipe.py lazily imports from shenas_pipes.spotify.auth which has been
# deleted. Create a stub module so the lazy imports inside pipe methods work
# during tests.
_fake_auth = types.ModuleType("shenas_pipes.spotify.auth")
_fake_auth.REDIRECT_URI = "http://127.0.0.1:8090/callback"  # type: ignore[attr-defined]
_fake_auth.SCOPES = "user-read-recently-played user-top-read user-library-read"  # type: ignore[attr-defined]
_fake_auth._pending_auth = {}  # type: ignore[attr-defined]


class _FakeCache:
    def __init__(self) -> None:
        self.token_info: dict | None = None

    def get_cached_token(self) -> dict | None:
        return self.token_info

    def save_token_to_cache(self, token_info: dict) -> None:
        self.token_info = token_info


_fake_auth._MemoryCacheHandler = _FakeCache  # type: ignore[attr-defined]
sys.modules["shenas_pipes.spotify.auth"] = _fake_auth

from shenas_pipes.spotify.pipe import SpotifyPipe  # noqa: E402


@pytest.fixture
def pipe() -> SpotifyPipe:
    p = SpotifyPipe.__new__(SpotifyPipe)
    p._auth_store = MagicMock()
    p._config_store = MagicMock()
    return p


class TestBuildClient:
    def test_no_tokens_raises(self, pipe: SpotifyPipe) -> None:
        pipe._auth_store.get.return_value = None
        with pytest.raises(RuntimeError, match="No Spotify tokens"):
            pipe.build_client()

    @patch("spotipy.Spotify")
    def test_returns_client(self, mock_spotify: MagicMock, pipe: SpotifyPipe) -> None:
        tokens = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": 9999999999,
            "client_id": "cid",
        }
        pipe._auth_store.get.return_value = {"tokens": json.dumps(tokens)}

        mock_pkce = MagicMock()
        mock_pkce.is_token_expired.return_value = False

        with patch("spotipy.oauth2.SpotifyPKCE", return_value=mock_pkce):
            pipe.build_client()

        mock_spotify.assert_called_once_with(auth="tok")


class TestAuthenticate:
    def test_missing_credentials(self, pipe: SpotifyPipe) -> None:
        with pytest.raises(ValueError, match="client_id is required"):
            pipe.authenticate({})

    def test_raises_oauth_url(self, pipe: SpotifyPipe) -> None:
        mock_pkce = MagicMock()
        mock_pkce.get_authorize_url.return_value = "https://accounts.spotify.com/authorize?foo=bar"

        mock_thread = MagicMock()
        with (
            patch("spotipy.oauth2.SpotifyPKCE", return_value=mock_pkce),
            patch("threading.Thread", return_value=mock_thread),
            pytest.raises(ValueError, match=r"OAUTH_URL:https://accounts.spotify.com/authorize"),
        ):
            pipe.authenticate({"client_id": "cid"})
