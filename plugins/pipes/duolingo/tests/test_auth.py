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
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjYzMDcyMDAwMDAsImlhdCI6MCwic3ViIjoxMjM0NX0.X"
        with patch(f"{MODULE}._get_stored_jwt", return_value=jwt):
            client = build_client()
        assert client._client.headers["Authorization"] == f"Bearer {jwt}"
        client.close()


class TestAuthenticate:
    def test_missing_token(self) -> None:
        with pytest.raises(ValueError, match="jwt_token is required"):
            authenticate({})

    @patch(f"{MODULE}._store_jwt")
    @patch(f"{MODULE}.DuolingoClient")
    def test_success(self, mock_cls: MagicMock, mock_store: MagicMock) -> None:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        authenticate({"jwt_token": "tok-123"})

        mock_cls.assert_called_once_with("tok-123")
        mock_store.assert_called_once_with("tok-123")
        mock_client.get_user.assert_called_once()
        mock_client.close.assert_called_once()

    @patch(f"{MODULE}.DuolingoClient")
    def test_invalid_token(self, mock_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.get_user.side_effect = Exception("401 Unauthorized")
        mock_cls.return_value = mock_client

        with pytest.raises(Exception, match="401"):
            authenticate({"jwt_token": "bad-token"})
        mock_client.close.assert_called_once()
