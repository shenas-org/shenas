"""Tests for model weight storage."""

from pathlib import Path

import numpy as np
import pytest

from fl_server.models import ModelStore


@pytest.fixture()
def store(tmp_path: Path) -> ModelStore:
    return ModelStore(weights_dir=tmp_path / "weights")


class TestModelStore:
    def test_save_and_load(self, store: ModelStore) -> None:
        weights = [np.array([1.0, 2.0, 3.0]), np.array([[4.0, 5.0], [6.0, 7.0]])]
        store.save("test-task", 0, weights)

        loaded = store.load_latest("test-task")
        assert loaded is not None
        assert len(loaded) == 2
        np.testing.assert_array_equal(loaded[0], weights[0])
        np.testing.assert_array_equal(loaded[1], weights[1])

    def test_load_specific_round(self, store: ModelStore) -> None:
        w0 = [np.array([1.0])]
        w1 = [np.array([2.0])]
        store.save("test-task", 0, w0)
        store.save("test-task", 1, w1)

        loaded = store.load_round("test-task", 0)
        assert loaded is not None
        np.testing.assert_array_equal(loaded[0], w0[0])

    def test_latest_round(self, store: ModelStore) -> None:
        assert store.latest_round("test-task") is None

        store.save("test-task", 0, [np.array([1.0])])
        assert store.latest_round("test-task") == 0

        store.save("test-task", 1, [np.array([2.0])])
        assert store.latest_round("test-task") == 1

    def test_load_nonexistent(self, store: ModelStore) -> None:
        assert store.load_latest("nonexistent") is None
        assert store.load_round("nonexistent", 0) is None

    def test_latest_symlink_updated(self, store: ModelStore) -> None:
        store.save("test-task", 0, [np.array([1.0])])
        store.save("test-task", 1, [np.array([2.0])])

        latest = store.load_latest("test-task")
        assert latest is not None
        np.testing.assert_array_equal(latest[0], np.array([2.0]))
