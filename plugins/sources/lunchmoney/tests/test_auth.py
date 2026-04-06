from unittest.mock import MagicMock, patch

import pytest

from shenas_sources.lunchmoney.pipe import LunchMoneySource


@pytest.fixture
def pipe() -> LunchMoneySource:
    p = LunchMoneySource.__new__(LunchMoneySource)
    p._auth_store = MagicMock()
    p._config_store = MagicMock()
    return p


class TestBuildClient:
    def test_no_key_raises(self, pipe: LunchMoneySource) -> None:
        pipe._auth_store.get.return_value = None
        with pytest.raises(RuntimeError, match="No API key"):
            pipe.build_client()

    @patch("lunchable.LunchMoney")
    def test_api_key_from_store(self, mock_lm_cls: MagicMock, pipe: LunchMoneySource) -> None:
        pipe._auth_store.get.return_value = {"api_key": "stored-key"}
        client = pipe.build_client()
        mock_lm_cls.assert_called_once_with(access_token="stored-key")
        assert client is mock_lm_cls.return_value


class TestAuthenticate:
    @patch("lunchable.LunchMoney")
    def test_stores_api_key(self, mock_lm_cls: MagicMock, pipe: LunchMoneySource) -> None:
        pipe.authenticate({"api_key": "test-key-123"})
        mock_lm_cls.assert_called_once_with(access_token="test-key-123")
        mock_lm_cls.return_value.get_user.assert_called_once()
        pipe._auth_store.set.assert_called_once_with(LunchMoneySource.Auth, api_key="test-key-123")

    def test_missing_key_raises(self, pipe: LunchMoneySource) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            pipe.authenticate({})
