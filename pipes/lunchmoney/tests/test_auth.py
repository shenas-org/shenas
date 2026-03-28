from unittest.mock import patch

import pytest

from shenas_pipes.lunchmoney.auth import build_client


class TestBuildClient:
    def test_no_key_raises(self) -> None:
        with patch("shenas_pipes.lunchmoney.auth._get_stored_key", return_value=None):
            with pytest.raises(RuntimeError, match="No API key"):
                build_client()

    @patch("shenas_pipes.lunchmoney.auth.LunchMoney")
    def test_api_key_stores_and_returns(self, mock_lm_cls) -> None:  # type: ignore[no-untyped-def]
        with patch("shenas_pipes.lunchmoney.auth._store_key") as mock_store:
            client = build_client(api_key="test-key-123")
        mock_store.assert_called_once_with("test-key-123")
        mock_lm_cls.assert_called_once_with(access_token="test-key-123")
        assert client is mock_lm_cls.return_value

    @patch("shenas_pipes.lunchmoney.auth.LunchMoney")
    def test_reads_from_keyring(self, mock_lm_cls) -> None:  # type: ignore[no-untyped-def]
        with patch("shenas_pipes.lunchmoney.auth._get_stored_key", return_value="stored-key"):
            client = build_client()
        mock_lm_cls.assert_called_once_with(access_token="stored-key")
        assert client is mock_lm_cls.return_value
