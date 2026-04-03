"""Federated learning strategies.

Wraps Flower's FedAvg with hooks that persist weights to the ModelStore
after each round.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flwr.common import (
    FitRes,
    Parameters,
    Scalar,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg

if TYPE_CHECKING:
    from fl_server.models import ModelStore
    from fl_server.tasks import Task

logger = logging.getLogger(__name__)


class ShenasStrategy(FedAvg):
    """FedAvg with model persistence after each aggregation round."""

    def __init__(self, task: Task, store: ModelStore, **kwargs: object) -> None:
        super().__init__(
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=task.min_clients,
            min_evaluate_clients=task.min_clients,
            min_available_clients=task.min_clients,
            **kwargs,
        )
        self.task = task
        self.store = store

    def aggregate_fit(
        self,
        server_round: int,
        results: list[tuple[ClientProxy, FitRes]],
        failures: list[tuple[ClientProxy, FitRes] | BaseException],
    ) -> tuple[Parameters | None, dict[str, Scalar]]:
        """Aggregate then persist the global weights."""
        parameters, metrics = super().aggregate_fit(server_round, results, failures)

        if parameters is not None:
            weights = parameters_to_ndarrays(parameters)
            self.store.save(
                self.task.name,
                server_round,
                weights,
                num_clients=len(results),
                metrics=dict(metrics) if metrics else None,
            )
            logger.info(
                "Round %d complete for %s: %d clients, %d failures",
                server_round,
                self.task.name,
                len(results),
                len(failures),
            )

        return parameters, metrics

    def initialize_parameters(self, client_manager: object) -> Parameters | None:
        """Load latest weights from store if available, otherwise let clients init."""
        existing = self.store.load_latest(self.task.name)
        if existing is not None:
            logger.info("Resuming %s from round %d", self.task.name, self.store.latest_round(self.task.name))
            return ndarrays_to_parameters(existing)
        return None
