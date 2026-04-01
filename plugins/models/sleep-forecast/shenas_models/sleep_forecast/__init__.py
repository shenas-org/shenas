"""Sleep forecast model plugin.

Predicts tomorrow's sleep score from recent HRV, activity, and vitals data.
Uses a two-layer neural network with ReLU activation.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class SleepForecastModel(nn.Module):
    """Two-layer network: features -> 16 hidden -> 1 output."""

    def __init__(self, n_features: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


MODEL = {
    "name": "sleep-forecast",
    "description": "Predict tomorrow's sleep score from HRV, activity, and vitals",
    "model_cls": SleepForecastModel,
    "features": ["rmssd", "sdnn", "resting_hr", "steps", "active_kcal"],
    "target": "score",
    "query": """
        SELECT
            s.score,
            h.rmssd, h.sdnn,
            v.resting_hr, v.steps, v.active_kcal
        FROM metrics.daily_sleep s
        JOIN metrics.daily_hrv h ON s.date = h.date + INTERVAL 1 DAY AND s.source = h.source
        JOIN metrics.daily_vitals v ON s.date = v.date + INTERVAL 1 DAY AND v.source = h.source
        WHERE s.score IS NOT NULL
        ORDER BY s.date
    """,
    "epochs": 5,
    "batch_size": 32,
    "learning_rate": 0.001,
}
