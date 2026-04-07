"""Tests for app.fl.inference -- InferenceEngine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from app.fl.inference import InferenceEngine


@pytest.fixture
def engine() -> InferenceEngine:
    return InferenceEngine(fl_api_url="http://fl", shenas_url="http://app")


class TestFetchWeights:
    def test_returns_none_on_non_200(self, engine: InferenceEngine) -> None:
        resp = MagicMock(status_code=404)
        with patch("httpx.get", return_value=resp):
            assert engine._fetch_weights("sleep") is None

    def test_returns_none_when_round_unchanged(self, engine: InferenceEngine) -> None:
        resp = MagicMock(status_code=200, json=lambda: {"round": 3})
        engine._rounds["sleep"] = 3
        with patch("httpx.get", return_value=resp):
            assert engine._fetch_weights("sleep") is None

    def test_returns_none_when_no_local_weights(self, engine: InferenceEngine, tmp_path) -> None:
        resp = MagicMock(status_code=200, json=lambda: {"round": 1})
        with (
            patch("httpx.get", return_value=resp),
            patch("app.fl.inference.WEIGHTS_CACHE", tmp_path / "client"),
            patch("pathlib.Path.exists", return_value=False),
        ):
            assert engine._fetch_weights("sleep") is None

    def test_loads_weights_when_present(self, engine: InferenceEngine, tmp_path) -> None:
        # Create a real .npz with two arrays
        npz_path = tmp_path / "latest.npz"
        np.savez(npz_path, a=np.zeros(4), b=np.ones(2))

        resp = MagicMock(status_code=200, json=lambda: {"round": 5})
        with (
            patch("httpx.get", return_value=resp),
            patch("app.fl.inference.WEIGHTS_CACHE", tmp_path / "client"),
            patch("pathlib.Path.exists", return_value=True),
            patch("numpy.load", return_value=np.load(npz_path)),
        ):
            result = engine._fetch_weights("sleep")
        assert result is not None
        weights, round_num = result
        assert round_num == 5
        assert len(weights) == 2
        assert engine._rounds["sleep"] == 5

    def test_swallows_exceptions(self, engine: InferenceEngine) -> None:
        with patch("httpx.get", side_effect=RuntimeError("boom")):
            assert engine._fetch_weights("sleep") is None


class TestPredict:
    def test_returns_none_on_task_lookup_failure(self, engine: InferenceEngine) -> None:
        with patch("httpx.get", return_value=MagicMock(status_code=404)):
            assert engine.predict("sleep") is None

    def test_returns_none_on_task_lookup_exception(self, engine: InferenceEngine) -> None:
        with patch("httpx.get", side_effect=RuntimeError("boom")):
            assert engine.predict("sleep") is None

    def test_returns_none_when_no_model_loaded(self, engine: InferenceEngine) -> None:
        task_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "features": ["f1"],
                "target": "y",
                "model": "linear",
                "query": "SELECT 1",
            },
        )
        with (
            patch("httpx.get", return_value=task_resp),
            patch.object(engine, "_fetch_weights", return_value=None),
        ):
            assert engine.predict("sleep") is None

    def test_returns_none_when_no_data(self, engine: InferenceEngine) -> None:
        engine._models["sleep"] = MagicMock(spec=torch.nn.Module)
        task_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "features": ["f1"],
                "target": "y",
                "model": "linear",
                "query": "SELECT 1",
            },
        )
        with (
            patch("httpx.get", return_value=task_resp),
            patch.object(engine, "_fetch_weights", return_value=None),
            patch.object(engine.fetcher, "fetch", return_value=None),
        ):
            assert engine.predict("sleep") is None

    def test_full_predict_path(self, engine: InferenceEngine) -> None:
        # Tiny linear model: 1 feature -> 1 prediction
        model = torch.nn.Linear(1, 1)
        engine._models["sleep"] = model
        engine._rounds["sleep"] = 7

        task_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "features": ["f1"],
                "target": "y",
                "model": "linear",
                "query": "SELECT 1",
            },
        )
        X = np.array([[1.0], [2.0], [3.0]], dtype=np.float32)
        y = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        with (
            patch("httpx.get", return_value=task_resp),
            patch.object(engine, "_fetch_weights", return_value=None),
            patch.object(engine.fetcher, "fetch", return_value=(X, y)),
        ):
            result = engine.predict("sleep")
        assert result is not None
        assert result["task"] == "sleep"
        assert result["round"] == 7
        assert result["n_samples"] == 3
        assert "mae" in result

    def test_loads_weights_when_available(self, engine: InferenceEngine) -> None:
        task_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "features": ["f1"],
                "target": "y",
                "model": "linear",
                "query": "SELECT 1",
            },
        )
        fake_model = torch.nn.Linear(1, 1)
        X = np.array([[1.0]], dtype=np.float32)
        y = np.array([1.0], dtype=np.float32)
        with (
            patch("httpx.get", return_value=task_resp),
            patch.object(engine, "_fetch_weights", return_value=([np.zeros(1)], 9)),
            patch("app.fl.inference.get_model", return_value=fake_model),
            patch("app.fl.inference.set_weights"),
            patch.object(engine.fetcher, "fetch", return_value=(X, y)),
        ):
            result = engine.predict("sleep")
        assert result is not None
        assert engine._models["sleep"] is fake_model


class TestListAvailable:
    def test_filters_to_tasks_with_a_round(self, engine: InferenceEngine) -> None:
        resp = MagicMock(
            status_code=200,
            json=lambda: [
                {"name": "sleep", "latest_round": 5, "features": ["f1"], "target": "y", "description": "d"},
                {"name": "stress", "latest_round": None, "features": ["f1"], "target": "y"},
            ],
        )
        with patch("httpx.get", return_value=resp):
            models = engine.list_available()
        assert len(models) == 1
        assert models[0]["name"] == "sleep"
        assert models[0]["round"] == 5

    def test_returns_empty_on_failure(self, engine: InferenceEngine) -> None:
        with patch("httpx.get", return_value=MagicMock(status_code=500)):
            assert engine.list_available() == []

    def test_returns_empty_on_exception(self, engine: InferenceEngine) -> None:
        with patch("httpx.get", side_effect=RuntimeError("boom")):
            assert engine.list_available() == []
