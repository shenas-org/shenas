from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.gmail.source import GmailSource


@pytest.fixture
def pipe() -> GmailSource:
    return GmailSource.__new__(GmailSource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(GmailSource.Auth, "read_row") as read,
        patch.object(GmailSource.Auth, "write_row") as write,
        patch.object(GmailSource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    @patch("shenas_sources.core.google_auth.GoogleAuth.build_client")
    def test_no_credentials_raises(self, mock_build_client: MagicMock, pipe: GmailSource) -> None:
        mock_build_client.side_effect = RuntimeError("No valid credentials")
        with pytest.raises(RuntimeError, match="No valid credentials"):
            pipe.build_client()

    @patch("shenas_sources.core.google_auth.GoogleAuth.build_client")
    def test_valid_token(self, mock_build_client: MagicMock, pipe: GmailSource) -> None:
        mock_service = MagicMock()
        mock_build_client.return_value = mock_service
        result = pipe.build_client()
        assert result is mock_service

    @patch("shenas_sources.core.google_auth.GoogleAuth.build_client")
    def test_calls_google_auth(self, mock_build_client: MagicMock, pipe: GmailSource) -> None:
        pipe.build_client()
        mock_build_client.assert_called_once()
