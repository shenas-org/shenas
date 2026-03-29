from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shenas_pipes.duolingo.auth import authenticate, build_client

MODULE = "shenas_pipes.duolingo.auth"


class TestBuildClient:
    def test_no_jwt_raises(self) -> None:
        with patch(f"{MODULE}._get_stored_jwt", return_value=None):
            with pytest.raises(RuntimeError, match="No JWT token"):
                build_client()

    def test_returns_client_with_jwt(self) -> None:
        with patch(f"{MODULE}._get_stored_jwt", return_value="fake-jwt"):
            client = build_client()
        assert client._client.headers["Authorization"] == "Bearer fake-jwt"
        client.close()


class TestAuthenticate:
    def test_missing_credentials(self) -> None:
        with pytest.raises(ValueError, match="username and password"):
            authenticate({})

    @patch(f"{MODULE}._store_jwt")
    @patch(f"{MODULE}.DuolingoClient")
    def test_success(self, mock_cls: MagicMock, mock_store: MagicMock) -> None:
        mock_cls.login.return_value = "jwt-123"
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        authenticate({"username": "user", "password": "pass"})

        mock_cls.login.assert_called_once_with("user", "pass")
        mock_store.assert_called_once_with("jwt-123")
        mock_client.get_user.assert_called_once()
        mock_client.close.assert_called_once()
