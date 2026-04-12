"""Shared model plugin utilities."""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from app.plugin import Plugin

logger = logging.getLogger(__name__)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.fl.inference import InferenceEngine

        _engine = InferenceEngine()
    return _engine


class Model(Plugin):
    """Base class for model plugins.

    Subclass this and set class attributes. The ``model_cls`` callable
    receives ``n_features`` and returns a ``torch.nn.Module``.
    """

    _kind = "model"

    model_cls: ClassVar[type]
    datasets: ClassVar[list[str]] = []
    features: ClassVar[list[str]] = []
    target: ClassVar[str] = ""
    query: ClassVar[str] = ""
    epochs: ClassVar[int] = 5
    batch_size: ClassVar[int] = 32
    learning_rate: ClassVar[float] = 0.001

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info.update(
            {
                "datasets": self.datasets,
                "features": self.features,
                "target": self.target,
                "epochs": self.epochs,
            }
        )
        return info

    @property
    def training_status(self) -> dict[str, Any]:
        """Check if trained weights are available via FL server."""
        try:
            for m in _get_engine().list_available():
                if m["name"] == self.name:
                    return {"name": self.name, "available": True, "round": m["round"]}
        except Exception:
            pass
        return {"name": self.name, "available": False, "round": None}

    def predict(self) -> dict | None:
        """Run prediction using the latest global model on local data."""
        return _get_engine().predict(self.name)
