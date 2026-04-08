from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.lunchmoney.source import LunchMoneySource


@pytest.fixture
def pipe() -> LunchMoneySource:
    return LunchMoneySource.__new__(LunchMoneySource)


@pytest.fixture
def auth_mock():
    with (
        patch.object(LunchMoneySource.Auth, "read_row") as read,
        patch.object(LunchMoneySource.Auth, "write_row") as write,
        patch.object(LunchMoneySource.Auth, "clear_rows") as clear,
    ):
        yield SimpleNamespace(read=read, write=write, clear=clear)


class TestBuildClient:
    def test_no_key_raises(self, pipe: LunchMoneySource, auth_mock) -> None:
        auth_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No API key"):
            pipe.build_client()

    @patch("lunchable.LunchMoney")
    def test_api_key_from_store(self, mock_lm_cls: MagicMock, pipe: LunchMoneySource, auth_mock) -> None:
        auth_mock.read.return_value = {"api_key": "stored-key"}
        client = pipe.build_client()
        mock_lm_cls.assert_called_once_with(access_token="stored-key")
        assert client is mock_lm_cls.return_value


class TestAuthenticate:
    @patch("lunchable.LunchMoney")
    def test_stores_api_key(self, mock_lm_cls: MagicMock, pipe: LunchMoneySource, auth_mock) -> None:
        pipe.authenticate({"api_key": "test-key-123"})
        mock_lm_cls.assert_called_once_with(access_token="test-key-123")
        mock_lm_cls.return_value.get_user.assert_called_once()
        auth_mock.write.assert_called_once_with(api_key="test-key-123")

    def test_missing_key_raises(self, pipe: LunchMoneySource) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            pipe.authenticate({})
