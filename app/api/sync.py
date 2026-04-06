"""Sync API endpoints with SSE streaming."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shenas_sources.core.source import Source

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.sources import _load_source
from app.models import ScheduleInfo, SyncRequest

if TYPE_CHECKING:
    from collections.abc import Iterator


router = APIRouter(prefix="/sync", tags=["sync"])

log = logging.getLogger(f"shenas.{__name__}")

SOURCE_PREFIX = "shenas-source-"


def _sse_event(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _installed_source_names() -> list[str]:
    """Get installed pipe names via uv pip list (avoids entry_points cache)."""

    result = subprocess.run(
        ["uv", "pip", "list", "--format", "json", "--python", sys.executable], capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    packages = json.loads(result.stdout)
    from app.api.sources import _load_plugin

    names = []
    for p in packages:
        if not p["name"].startswith(SOURCE_PREFIX):
            continue
        name = p["name"].removeprefix(SOURCE_PREFIX)
        cls = _load_plugin("source", name)
        if cls and not cls.internal and name != "core" and cls().enabled:
            names.append(name)
    return names


def _run_pipe_sync(
    pipe: Source,
    full_refresh: bool,
) -> Iterator[str]:
    """Run a single pipe's sync, yielding SSE events.

    Locking and synced_at bookkeeping are handled by the Pipe ABC.
    """
    log.info("Sync started: %s", pipe.name)
    yield _sse_event("progress", {"source": pipe.name, "message": "starting sync"})

    if pipe.has_auth and not pipe.is_authenticated:
        msg = "Not authenticated. Configure credentials in the Auth tab."
        log.warning("Sync skipped: %s -- %s", pipe.name, msg)
        yield _sse_event("error", {"source": pipe.name, "message": msg})
        return

    try:
        pipe.sync(full_refresh=full_refresh)
        log.info("Sync complete: %s", pipe.name)
        yield _sse_event("complete", {"source": pipe.name, "message": "done"})
    except Exception as exc:
        log.exception("Sync failed: %s", pipe.name)
        yield _sse_event("error", {"source": pipe.name, "message": str(exc)})


@router.post("")
def sync_all() -> StreamingResponse:
    def _stream() -> Iterator[str]:
        failed = []
        for name in _installed_source_names():
            try:
                pipe = _load_source(name)
            except Exception as exc:
                yield _sse_event("error", {"source": name, "message": str(exc)})
                failed.append(name)
                continue

            if not pipe.acquire_sync_lock():
                yield _sse_event("progress", {"source": name, "message": "skipping: sync already in progress"})
                continue
            try:
                yield from _run_pipe_sync(pipe, full_refresh=False)
            except Exception as exc:
                yield _sse_event("error", {"source": name, "message": str(exc)})
                failed.append(name)
            finally:
                pipe.release_sync_lock()

        if failed:
            yield _sse_event("error", {"message": f"Failed: {', '.join(failed)}"})
        else:
            yield _sse_event("complete", {"message": "all syncs complete"})

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/{name}")
def sync_pipe(name: str, body: SyncRequest | None = None) -> StreamingResponse:
    body = body or SyncRequest()

    if name not in _installed_source_names():
        raise HTTPException(status_code=404, detail=f"Source not found: {name}")

    pipe = _load_source(name)

    if not pipe.acquire_sync_lock():
        raise HTTPException(status_code=409, detail="Sync already in progress")

    def _stream() -> Iterator[str]:
        try:
            yield from _run_pipe_sync(pipe, body.full_refresh)
        except Exception as exc:
            yield _sse_event("error", {"source": name, "message": str(exc)})
        finally:
            pipe.release_sync_lock()

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.get("/schedule")
def get_sync_schedule() -> list[ScheduleInfo]:
    """Return schedule status for all pipes with a sync frequency configured."""
    from app.db import get_all_sync_schedules

    return [ScheduleInfo(**row) for row in get_all_sync_schedules()]
