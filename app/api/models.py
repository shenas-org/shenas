"""Model prediction proxy endpoints.

Proxies requests to the local fl-client inference API (port 8082).
The fl-client has PyTorch and the trained model weights; the app server
does not need torch as a dependency.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/models", tags=["models"])

log = logging.getLogger(f"shenas.{__name__}")

FL_CLIENT_URL = "http://127.0.0.1:8082"


def _proxy_get(path: str) -> Any:
    """Forward a GET request to the fl-client inference API."""
    try:
        resp = httpx.get(f"{FL_CLIENT_URL}{path}", timeout=10.0)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail=resp.json().get("detail", "Not found"))
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="FL client inference service not running")


@router.get("/")
def list_models() -> list[dict]:
    """List models with trained weights available."""
    return _proxy_get("/api/models")


@router.get("/{name}/predict")
def predict(name: str) -> dict:
    """Run prediction using the latest global model on local data."""
    return _proxy_get(f"/api/models/{name}/predict")


@router.get("/{name}/status")
def model_status(name: str) -> dict:
    """Get model training status."""
    return _proxy_get(f"/api/models/{name}/status")
