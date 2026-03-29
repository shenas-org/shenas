from __future__ import annotations

from unittest.mock import patch

import pytest

from shenas_pipes.strava.auth import authenticate, build_client

MODULE = "shenas_pipes.strava.auth"


class TestBuildClient:
    def test_no_tokens_raises(self) -> None:
        with patch(f"{MODULE}._get_stored_tokens", return_value=None):
            with pytest.raises(RuntimeError, match="No Strava tokens"):
                build_client()

    def test_returns_client(self) -> None:
        tokens = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": 9999999999,
            "client_id": "123",
            "client_secret": "sec",
        }
        with (
            patch(f"{MODULE}._get_stored_tokens", return_value=tokens),
            patch("shenas_pipes.strava.client.build_strava_client") as mock_build,
        ):
            build_client()
            mock_build.assert_called_once()


class TestAuthenticate:
    def test_missing_credentials(self) -> None:
        with pytest.raises(ValueError, match="client_id and client_secret"):
            authenticate({})

    def test_raises_oauth_url(self) -> None:
        with pytest.raises(ValueError, match="OAUTH_URL:https://www.strava.com/oauth/authorize"):
            authenticate({"client_id": "123", "client_secret": "sec"})
