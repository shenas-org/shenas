"""Tests for local model training."""

import numpy as np

from fl_client.trainer import LinearModel, evaluate, get_model, get_weights, set_weights, train


class TestModel:
    def test_linear_model_forward(self) -> None:
        model = LinearModel(n_features=3)
        import torch

        x = torch.randn(5, 3)
        out = model(x)
        assert out.shape == (5,)

    def test_get_model_linear(self) -> None:
        model = get_model("linear", 4)
        assert isinstance(model, LinearModel)

    def test_get_model_unknown(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Unknown model"):
            get_model("transformer", 4)


class TestWeights:
    def test_round_trip(self) -> None:
        model = LinearModel(n_features=3)
        weights = get_weights(model)
        assert len(weights) == 2  # weight matrix + bias

        # Modify and set back
        new_weights = [np.ones_like(w) for w in weights]
        set_weights(model, new_weights)
        restored = get_weights(model)
        for w, expected in zip(restored, new_weights):
            np.testing.assert_array_almost_equal(w, expected)


class TestTrain:
    def test_train_reduces_loss(self) -> None:
        np.random.seed(42)
        X = np.random.randn(100, 3).astype(np.float32)
        y = (X[:, 0] * 2 + X[:, 1] * -1 + 0.5).astype(np.float32)

        model = LinearModel(n_features=3)
        metrics = train(model, X, y, epochs=50, batch_size=32, lr=0.01)
        assert metrics["loss"] < 5.0  # should converge somewhat
        assert metrics["num-examples"] == 100


class TestEvaluate:
    def test_evaluate_returns_metrics(self) -> None:
        X = np.random.randn(50, 3).astype(np.float32)
        y = np.random.randn(50).astype(np.float32)

        model = LinearModel(n_features=3)
        metrics = evaluate(model, X, y)
        assert "loss" in metrics
        assert "mae" in metrics
        assert metrics["num-examples"] == 50
