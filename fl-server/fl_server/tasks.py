"""Task definitions for federated learning.

A task describes what model to train, which data columns to use, and
training hyperparameters. Tasks are stored in-memory for now (Phase 1).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Task:
    """A federated learning task definition."""

    name: str
    description: str
    # Model architecture identifier (resolved by model plugins on clients)
    model: str
    # SQL query clients run against their local DuckDB to get training data.
    # Must return a table with the columns listed in `features` + `target`.
    query: str
    # Column names used as input features
    features: list[str]
    # Column name for the prediction target
    target: str
    # Training hyperparameters
    epochs: int = 3
    batch_size: int = 32
    learning_rate: float = 0.001
    # FL round configuration
    num_rounds: int = 10
    min_clients: int = 2


# Built-in tasks for Phase 1. Later these come from an API/database.
DEFAULT_TASKS: dict[str, Task] = {
    "sleep-forecast": Task(
        name="sleep-forecast",
        description="Predict tomorrow's sleep score from recent HRV, activity, and vitals",
        model="linear",
        query="""
            SELECT
                s.score as target,
                h.rmssd, h.sdnn,
                v.resting_hr, v.steps, v.active_kcal
            FROM metrics.daily_sleep s
            JOIN metrics.daily_hrv h ON s.date = h.date + INTERVAL 1 DAY AND s.source = h.source
            JOIN metrics.daily_vitals v ON s.date = v.date + INTERVAL 1 DAY AND v.source = h.source
            WHERE s.score IS NOT NULL
            ORDER BY s.date
        """,
        features=["rmssd", "sdnn", "resting_hr", "steps", "active_kcal"],
        target="target",
        epochs=5,
        num_rounds=10,
        min_clients=2,
    ),
}


_tasks: dict[str, Task] = dict(DEFAULT_TASKS)


def get_task(name: str) -> Task | None:
    return _tasks.get(name)


def list_tasks() -> list[Task]:
    return list(_tasks.values())


def add_task(task: Task) -> None:
    _tasks[task.name] = task


def remove_task(name: str) -> bool:
    return _tasks.pop(name, None) is not None
