"""FastAPI auth and API service for shenas.net."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from shenas_web_api.auth import router as auth_router
from shenas_web_api.config import FRONTEND_URL, SESSION_SECRET
from shenas_web_api.db import ensure_schema

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_schema()
    yield


app = FastAPI(lifespan=_lifespan, docs_url=None, redoc_url=None)

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def cli() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    cli()
