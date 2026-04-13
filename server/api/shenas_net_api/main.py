"""FastAPI auth and API service for shenas.net."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from shenas_net_api.auth import router as auth_router
from shenas_net_api.config import FRONTEND_URL, SESSION_SECRET
from shenas_net_api.db import ensure_schema
from shenas_net_api.devices import router as devices_router
from shenas_net_api.literature import router as literature_router
from shenas_net_api.llm import router as llm_router
from shenas_net_api.logging_setup import init_logging
from shenas_net_api.packages import router as packages_router
from shenas_net_api.relay import router as relay_router
from shenas_net_api.workers import router as workers_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

init_logging()
log = logging.getLogger("shenas-net-api")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    log.info("Starting shenas-net-api")
    ensure_schema()
    log.info("Schema ready")
    yield
    log.info("Shutting down")


app = FastAPI(lifespan=_lifespan, docs_url=None, redoc_url=None)


@app.middleware("http")
async def _log_requests(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    """Log every request with method, path, status, and elapsed time."""
    start = time.monotonic()
    response: Response = await call_next(request)
    elapsed = (time.monotonic() - start) * 1000
    path = request.url.path
    if path != "/api/health":
        log.info("%s %s %d %.0fms", request.method, path, response.status_code, elapsed)
    return response


app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api")
app.include_router(devices_router, prefix="/api")
app.include_router(literature_router, prefix="/api")
app.include_router(llm_router, prefix="/api")
app.include_router(relay_router, prefix="/api")
app.include_router(workers_router, prefix="/api")
app.include_router(packages_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def cli() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    cli()
