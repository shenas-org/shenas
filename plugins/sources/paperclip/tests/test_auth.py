from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.paperclip.source import PaperclipSource


@pytest.fixture
def source() -> PaperclipSource:
    return PaperclipSource.__new__(PaperclipSource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(PaperclipSource.Auth, "read_row") as read,
        patch.object(PaperclipSource.Auth, "write_row") as write,
        patch.object(PaperclipSource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    def test_no_tokens_raises(self, source: PaperclipSource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No credentials found"):
            source.build_client()

    def test_empty_tokens_raises(self, source: PaperclipSource, auth_mock) -> None:
        auth_mock.read.return_value = {"tokens": None}
        with pytest.raises(RuntimeError, match="No credentials found"):
            source.build_client()

    @patch("shenas_sources.paperclip.client.PaperclipClient")
    def test_valid_tokens_returns_client(self, mock_cls: MagicMock, source: PaperclipSource, auth_mock) -> None:
        import json

        creds = json.dumps({"api_url": "http://127.0.0.1:3100", "api_key": "test-key"})
        auth_mock.read.return_value = {"tokens": creds}

        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        result = source.build_client()

        assert result is mock_client
        mock_cls.assert_called_once_with("http://127.0.0.1:3100", "test-key")


class TestAuthenticate:
    def test_missing_api_key_raises(self, source: PaperclipSource, auth_mock) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            source.authenticate({"api_url": "http://127.0.0.1:3100", "api_key": ""})

    @patch("shenas_sources.paperclip.client.PaperclipClient")
    def test_successful_auth_stores_tokens(self, mock_cls: MagicMock, source: PaperclipSource, auth_mock) -> None:
        import json

        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        source.authenticate({"api_url": "http://127.0.0.1:3100", "api_key": "valid-key"})

        mock_client.get_me.assert_called_once()
        mock_client.close.assert_called_once()
        auth_mock.write.assert_called_once()
        stored = json.loads(auth_mock.write.call_args.kwargs["tokens"])
        assert stored["api_url"] == "http://127.0.0.1:3100"
        assert stored["api_key"] == "valid-key"

    @patch("shenas_sources.paperclip.client.PaperclipClient")
    def test_default_api_url_used_when_blank(self, mock_cls: MagicMock, source: PaperclipSource, auth_mock) -> None:
        import json

        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        source.authenticate({"api_url": "", "api_key": "valid-key"})

        stored = json.loads(auth_mock.write.call_args.kwargs["tokens"])
        assert stored["api_url"] == "http://127.0.0.1:3100"

    @patch("shenas_sources.paperclip.client.PaperclipClient")
    def test_bad_token_raises_value_error(self, mock_cls: MagicMock, source: PaperclipSource, auth_mock) -> None:
        import httpx

        mock_client = MagicMock()
        mock_client.get_me.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )
        mock_cls.return_value = mock_client

        with pytest.raises(ValueError, match="401"):
            source.authenticate({"api_url": "http://127.0.0.1:3100", "api_key": "bad-key"})

        mock_client.close.assert_called_once()
        auth_mock.write.assert_not_called()
