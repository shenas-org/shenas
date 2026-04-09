from types import SimpleNamespace
from unittest.mock import patch

import pytest

from shenas_sources.goodreads.source import GoodreadsSource


@pytest.fixture
def pipe() -> GoodreadsSource:
    return GoodreadsSource.__new__(GoodreadsSource)


@pytest.fixture
def config_mock():
    with (
        patch.object(GoodreadsSource.Config, "read_row") as read,
        patch.object(GoodreadsSource.Config, "write_row") as write,
    ):
        yield SimpleNamespace(read=read, write=write)


class TestBuildClient:
    def test_no_user_id_raises(self, pipe: GoodreadsSource, config_mock) -> None:
        config_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No user_id configured"):
            pipe.build_client()

    def test_empty_user_id_raises(self, pipe: GoodreadsSource, config_mock) -> None:
        config_mock.read.return_value = {"user_id": ""}
        with pytest.raises(RuntimeError, match="No user_id configured"):
            pipe.build_client()

    @patch("shenas_sources.goodreads.client.GoodreadsClient")
    def test_valid_user_id_returns_client(self, mock_cls, pipe: GoodreadsSource, config_mock) -> None:
        config_mock.read.return_value = {"user_id": "12345"}
        mock_client = mock_cls.return_value
        result = pipe.build_client()
        assert result is mock_client
        mock_cls.assert_called_once_with("12345")


class TestSource:
    def test_has_no_auth(self) -> None:
        pipe = GoodreadsSource.__new__(GoodreadsSource)
        assert not pipe.has_auth
