"""Local model training and evaluation.

Supports a simple linear model for Phase 1. Model plugins (Phase 3)
will provide custom architectures.
"""

from __future__ import annotations

import logging

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class LinearModel(nn.Module):
    """Simple linear regression model for tabular data."""

    def __init__(self, n_features: int) -> None:
        super().__init__()
        self.linear = nn.Linear(n_features, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x).squeeze(-1)


def get_model(name: str, n_features: int) -> nn.Module:
    """Get a model by name. Phase 1 only supports 'linear'."""
    if name == "linear":
        return LinearModel(n_features)
    raise ValueError(f"Unknown model: {name}. Available: linear")


def get_weights(model: nn.Module) -> list[np.ndarray]:
    """Extract model weights as a list of numpy arrays."""
    return [val.cpu().numpy() for _, val in model.state_dict().items()]


def set_weights(model: nn.Module, weights: list[np.ndarray]) -> None:
    """Set model weights from a list of numpy arrays."""
    state_dict = model.state_dict()
    for (key, _), w in zip(state_dict.items(), weights):
        state_dict[key] = torch.tensor(w)
    model.load_state_dict(state_dict)


def train(
    model: nn.Module,
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 3,
    batch_size: int = 32,
    lr: float = 0.001,
) -> dict[str, float]:
    """Train the model on local data. Returns metrics dict."""
    device = torch.device("cpu")
    model = model.to(device)
    model.train()

    X_t = torch.tensor(X, dtype=torch.float32, device=device)
    y_t = torch.tensor(y, dtype=torch.float32, device=device)

    # Normalize features
    mean = X_t.mean(dim=0)
    std = X_t.std(dim=0).clamp(min=1e-6)
    X_t = (X_t - mean) / std

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    total_loss = 0.0
    n_batches = 0

    for epoch in range(epochs):
        perm = torch.randperm(len(X_t))
        for i in range(0, len(X_t), batch_size):
            batch_idx = perm[i : i + batch_size]
            X_batch = X_t[batch_idx]
            y_batch = y_t[batch_idx]

            optimizer.zero_grad()
            pred = model(X_batch)
            loss = loss_fn(pred, y_batch)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

    avg_loss = total_loss / max(n_batches, 1)
    logger.info("Trained %d epochs, avg loss: %.4f", epochs, avg_loss)

    return {"loss": avg_loss, "num-examples": len(X)}


def evaluate(model: nn.Module, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Evaluate model on local data. Returns metrics dict."""
    device = torch.device("cpu")
    model = model.to(device)
    model.eval()

    X_t = torch.tensor(X, dtype=torch.float32, device=device)
    y_t = torch.tensor(y, dtype=torch.float32, device=device)

    mean = X_t.mean(dim=0)
    std = X_t.std(dim=0).clamp(min=1e-6)
    X_t = (X_t - mean) / std

    with torch.no_grad():
        pred = model(X_t)
        mse = nn.MSELoss()(pred, y_t).item()
        mae = (pred - y_t).abs().mean().item()

    return {"loss": mse, "mae": mae, "num-examples": len(X)}
