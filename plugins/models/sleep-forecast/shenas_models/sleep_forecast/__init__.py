"""Sleep forecast model plugin.

Predicts tomorrow's sleep score from recent HRV, activity, and vitals data.
Uses a two-layer neural network with ReLU activation.
"""

from __future__ import annotations

from typing import ClassVar

import torch
from torch import nn

from shenas_models.core import Model


class SleepForecastNet(nn.Module):
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


class SleepForecast(Model):
    name = "sleep-forecast"
    display_name = "Sleep Forecast"
    description = "Predict tomorrow's sleep score from HRV, activity, and vitals"
    model_cls = SleepForecastNet
    datasets: ClassVar[list[str]] = ["fitness"]
    features: ClassVar[list[str]] = ["rmssd", "sdnn", "resting_hr", "steps", "active_kcal"]
    target = "score"
    query = """
        SELECT
            s.score,
            h.rmssd, h.sdnn,
            v.resting_hr, v.steps, v.active_kcal
        FROM metrics.daily_sleep s
        JOIN metrics.daily_hrv h ON s.date = h.date + INTERVAL 1 DAY AND s.source = h.source
        JOIN metrics.daily_vitals v ON s.date = v.date + INTERVAL 1 DAY AND v.source = h.source
        WHERE s.score IS NOT NULL
        ORDER BY s.date
    """
