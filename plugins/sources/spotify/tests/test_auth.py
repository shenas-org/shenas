from __future__ import annotations

import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# The source module lazily imports from shenas_sources.spotify.auth which has
# been deleted. Create a stub module so the lazy imports inside source methods
# work during tests.
_fake_auth = types.ModuleType("shenas_sources.spotify.auth")
_fake_auth.REDIRECT_URI = "http://127.0.0.1:8090/callback"  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]
_fake_auth.SCOPES = "user-read-recently-played user-top-read user-library-read"  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]
_fake_auth._pending_auth = {}  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]


class _FakeCache:
    def __init__(self) -> None:
        self.token_info: dict | None = None

    def get_cached_token(self) -> dict | None:
        return self.token_info

    def save_token_to_cache(self, token_info: dict) -> None:
        self.token_info = token_info


_fake_auth._MemoryCacheHandler = _FakeCache  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]
sys.modules["shenas_sources.spotify.auth"] = _fake_auth

from shenas_sources.spotify.source import SpotifySource  # noqa: E402


@pytest.fixture
def source() -> SpotifySource:
    return SpotifySource.__new__(SpotifySource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(SpotifySource.Auth, "read_row") as read,
        patch.object(SpotifySource.Auth, "write_row") as write,
        patch.object(SpotifySource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    def test_no_tokens_raises(self, source: SpotifySource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No Spotify tokens"):
            source.build_client()

    @patch("spotipy.Spotify")
    def test_returns_client(self, mock_spotify: MagicMock, source: SpotifySource, auth_mock) -> None:
        tokens = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": 9999999999,
            "client_id": "cid",
        }
        auth_mock.read.return_value = {"tokens": json.dumps(tokens)}

        mock_pkce = MagicMock()
        mock_pkce.is_token_expired.return_value = False

        with patch("spotipy.oauth2.SpotifyPKCE", return_value=mock_pkce):
            source.build_client()

        mock_spotify.assert_called_once_with(auth="tok")


class TestAuthenticate:
    def test_missing_credentials(self, source: SpotifySource) -> None:
        with pytest.raises(ValueError, match="client_id is required"):
            source.authenticate({})

    def test_raises_oauth_url(self, source: SpotifySource) -> None:
        mock_pkce = MagicMock()
        mock_pkce.get_authorize_url.return_value = "https://accounts.spotify.com/authorize?foo=bar"

        mock_thread = MagicMock()
        with (
            patch("spotipy.oauth2.SpotifyPKCE", return_value=mock_pkce),
            patch("threading.Thread", return_value=mock_thread),
            pytest.raises(ValueError, match=r"OAUTH_URL:https://accounts.spotify.com/authorize"),
        ):
            source.authenticate({"client_id": "cid"})
