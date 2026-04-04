"""Flower server and REST API for federated learning coordination.

Runs two services:
- Flower gRPC server (default port 8080) for FL client communication
- FastAPI REST API (default port 8081) for task management and model access
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import flwr as fl
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from flwr.server import ServerConfig

from fl_server.models import ModelStore
from fl_server.strategy import ShenasStrategy
from fl_server.tasks import get_task, list_tasks

if TYPE_CHECKING:
    from fl_server.auth import ClientRegistry

logger = logging.getLogger(__name__)

api = FastAPI(title="shenas-fl", description="Federated learning coordinator")


def _get_store() -> ModelStore:
    return api.state.store


def _get_registry() -> ClientRegistry:
    return api.state.registry


def _require_auth(request: Request) -> str:
    """Dependency that verifies the Bearer token. Returns client name."""
    registry: ClientRegistry = request.app.state.registry
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth[7:]
    client_name = registry.verify(token)
    if client_name is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return client_name


# ---- Client management (admin, no auth required -- run on trusted network) ----


@api.post("/api/fl/clients")
def register_client(name: str) -> dict:
    """Register a new FL client. Returns the auth token (shown once)."""
    token = _get_registry().register(name)
    return {"name": name, "token": token}


@api.get("/api/fl/clients")
def list_clients() -> list[str]:
    """List registered client names."""
    return _get_registry().list_clients()


@api.delete("/api/fl/clients/{name}")
def revoke_client(name: str) -> dict:
    """Revoke a client's access."""
    if _get_registry().revoke(name):
        return {"ok": True, "message": f"Revoked {name}"}
    raise HTTPException(status_code=404, detail=f"Client '{name}' not found")


# ---- Task & model endpoints (auth required) ----


@api.get("/api/fl/tasks")
def api_list_tasks(_client: Annotated[str, Depends(_require_auth)]) -> list[dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "model": t.model,
            "num_rounds": t.num_rounds,
            "min_clients": t.min_clients,
            "features": t.features,
            "target": t.target,
            "latest_round": _get_store().latest_round(t.name),
        }
        for t in list_tasks()
    ]


@api.get("/api/fl/tasks/{name}")
def api_get_task(name: str, _client: Annotated[str, Depends(_require_auth)]) -> dict:
    task = get_task(name)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{name}' not found")
    store = _get_store()
    return {
        "name": task.name,
        "description": task.description,
        "model": task.model,
        "query": task.query,
        "features": task.features,
        "target": task.target,
        "epochs": task.epochs,
        "batch_size": task.batch_size,
        "learning_rate": task.learning_rate,
        "num_rounds": task.num_rounds,
        "min_clients": task.min_clients,
        "latest_round": store.latest_round(task.name),
    }


@api.get("/api/fl/tasks/{name}/weights")
def api_get_weights(
    name: str,
    _client: Annotated[str, Depends(_require_auth)],
    round_num: Annotated[int | None, Query(alias="round")] = None,
) -> dict:
    """Get model weight metadata. Actual weights downloaded via Flower protocol."""
    store = _get_store()
    if round_num is not None:
        weights = store.load_round(name, round_num)
    else:
        weights = store.load_latest(name)
        round_num = store.latest_round(name)
    if weights is None:
        raise HTTPException(status_code=404, detail="No weights available")
    return {
        "task": name,
        "round": round_num,
        "num_arrays": len(weights),
        "shapes": [list(w.shape) for w in weights],
        "total_params": sum(w.size for w in weights),
    }


@api.get("/api/fl/tasks/{name}/history")
def api_task_history(name: str, _client: Annotated[str, Depends(_require_auth)]) -> list[dict]:
    """Get version history for a task (all completed rounds with metadata)."""
    return _get_store().history(name)


@api.get("/api/fl/health")
def api_health() -> dict:
    return {"status": "ok", "tasks": len(list_tasks())}


# ---- Flower server ----


def start_fl_server(
    task_name: str,
    grpc_address: str = "0.0.0.0:8080",
    weights_dir: Path = Path(".shenas-fl/weights"),
) -> None:
    """Start a Flower server for a specific task (blocking)."""
    task = get_task(task_name)
    if task is None:
        raise ValueError(f"Unknown task: {task_name}")

    store = ModelStore(weights_dir=weights_dir)
    strategy = ShenasStrategy(task=task, store=store)

    logger.info("Starting Flower server for task '%s' on %s (%d rounds)", task.name, grpc_address, task.num_rounds)

    fl.server.start_server(
        server_address=grpc_address,
        config=ServerConfig(num_rounds=task.num_rounds),
        strategy=strategy,
    )


def start_fl_server_background(
    task_name: str,
    grpc_address: str = "0.0.0.0:8080",
    weights_dir: Path = Path(".shenas-fl/weights"),
) -> threading.Thread:
    """Start the Flower server in a background thread."""
    thread = threading.Thread(
        target=start_fl_server,
        args=(task_name, grpc_address, weights_dir),
        daemon=True,
        name=f"fl-server-{task_name}",
    )
    thread.start()
    return thread
