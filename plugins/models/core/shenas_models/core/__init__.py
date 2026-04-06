"""Shared model plugin utilities."""

from __future__ import annotations

from typing import Any, ClassVar

from shenas_plugins.core.plugin import Plugin


class Model(Plugin):
    """Base class for model plugins.

    Subclass this and set class attributes. The ``model_cls`` callable
    receives ``n_features`` and returns a ``torch.nn.Module``.
    """

    _kind = "model"

    model_cls: ClassVar[type]
    schemas: ClassVar[list[str]] = []
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
                "schemas": self.schemas,
                "features": self.features,
                "target": self.target,
                "epochs": self.epochs,
            }
        )
        return info
