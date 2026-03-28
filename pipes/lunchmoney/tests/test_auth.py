from pathlib import Path
from unittest.mock import patch

import pytest

from shenas_pipes.lunchmoney.auth import build_client


class TestBuildClient:
    def test_no_key_no_file_raises(self, tmp_path: Path) -> None:
        token_store = str(tmp_path / "token")
        with pytest.raises(RuntimeError, match="No API key"):
            build_client(token_store=token_store)

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        token_file = tmp_path / "token"
        token_file.write_text("")
        with pytest.raises(RuntimeError, match="No API key"):
            build_client(token_store=str(token_file))

    @patch("shenas_pipes.lunchmoney.auth.LunchMoney")
    def test_api_key_saves_and_returns(self, mock_lm_cls, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        token_file = tmp_path / "token"
        client = build_client(api_key="test-key-123", token_store=str(token_file))
        assert token_file.read_text() == "test-key-123"
        mock_lm_cls.assert_called_once_with(access_token="test-key-123")
        assert client is mock_lm_cls.return_value

    @patch("shenas_pipes.lunchmoney.auth.LunchMoney")
    def test_reads_stored_key(self, mock_lm_cls, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        token_file = tmp_path / "token"
        token_file.write_text("stored-key-456\n")
        client = build_client(token_store=str(token_file))
        mock_lm_cls.assert_called_once_with(access_token="stored-key-456")
        assert client is mock_lm_cls.return_value
