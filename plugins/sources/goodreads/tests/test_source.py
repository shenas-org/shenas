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


class TestSync:
    def test_no_csv_path_raises(self, pipe: GoodreadsSource, config_mock) -> None:
        config_mock.read.return_value = None
        with pytest.raises(RuntimeError, match="No csv_path configured"):
            pipe.sync()

    def test_missing_file_raises(self, pipe: GoodreadsSource, config_mock) -> None:
        config_mock.read.return_value = {"csv_path": "/nonexistent/file.csv"}
        with pytest.raises(RuntimeError, match="CSV file not found"):
            pipe.sync()

    def test_has_no_auth(self) -> None:
        pipe = GoodreadsSource.__new__(GoodreadsSource)
        assert not pipe.has_auth
