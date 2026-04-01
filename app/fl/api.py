"""REST API for local inference.

Runs alongside the FL client daemon, serving predictions from the
latest global model. The shenas app server can proxy to this.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.fl.inference import InferenceEngine

api = FastAPI(title="shenas-fl-client", description="Local federated learning inference")


def _engine() -> InferenceEngine:
    return api.state.engine


@api.get("/api/models")
def list_models() -> list[dict]:
    """List models with trained weights available."""
    return _engine().list_available()


@api.get("/api/models/{name}/predict")
def predict(name: str) -> dict:
    """Run prediction using the latest global model on local data."""
    result = _engine().predict(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No trained model available for '{name}'")
    return result


@api.get("/api/models/{name}/status")
def model_status(name: str) -> dict:
    """Get status of a model (round number, availability)."""
    engine = _engine()
    available = engine.list_available()
    for m in available:
        if m["name"] == name:
            return {"name": name, "available": True, "round": m["round"]}
    return {"name": name, "available": False, "round": None}


@api.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
