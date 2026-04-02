"""Model prediction endpoints.

Uses the FL inference engine directly (app.fl.inference) -- no separate
service needed since flwr is now in the workspace via dependency override.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/models", tags=["models"])

log = logging.getLogger(f"shenas.{__name__}")

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.fl.inference import InferenceEngine

        _engine = InferenceEngine()
    return _engine


@router.get("/")
def list_models() -> list[dict]:
    """List models with trained weights available."""
    return _get_engine().list_available()


@router.get("/{name}/predict")
def predict(name: str) -> dict:
    """Run prediction using the latest global model on local data."""
    result = _get_engine().predict(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No trained model available for '{name}'")
    return result


@router.get("/{name}/status")
def model_status(name: str) -> dict:
    """Get model training status."""
    engine = _get_engine()
    available = engine.list_available()
    for m in available:
        if m["name"] == name:
            return {"name": name, "available": True, "round": m["round"]}
    return {"name": name, "available": False, "round": None}
