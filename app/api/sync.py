"""Sync API endpoints with SSE streaming."""

from __future__ import annotations

import contextlib
import json
import logging
import subprocess
import sys
import threading
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.pipes import _load_pipe
from app.models import ScheduleInfo, SyncRequest

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_pipes.core.abc import Pipe

router = APIRouter(prefix="/sync", tags=["sync"])

log = logging.getLogger(f"shenas.{__name__}")

PIPE_PREFIX = "shenas-pipe-"

# Per-pipe sync lock to prevent concurrent syncs of the same pipe
_sync_locks: dict[str, threading.Lock] = {}
_sync_locks_guard = threading.Lock()


def acquire_sync_lock(name: str) -> bool:
    """Try to acquire the sync lock for a pipe. Returns False if already locked."""
    with _sync_locks_guard:
        if name not in _sync_locks:
            _sync_locks[name] = threading.Lock()
    return _sync_locks[name].acquire(blocking=False)


def release_sync_lock(name: str) -> None:
    """Release the sync lock for a pipe."""
    with _sync_locks_guard:
        lock = _sync_locks.get(name)
    if lock is not None:
        with contextlib.suppress(RuntimeError):
            lock.release()


def _sse_event(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _installed_pipe_names() -> list[str]:
    """Get installed pipe names via uv pip list (avoids entry_points cache)."""

    result = subprocess.run(
        ["uv", "pip", "list", "--format", "json", "--python", sys.executable], capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    packages = json.loads(result.stdout)
    from app.api.pipes import _load_plugin
    from app.db import is_plugin_enabled

    names = []
    for p in packages:
        if not p["name"].startswith(PIPE_PREFIX):
            continue
        name = p["name"].removeprefix(PIPE_PREFIX)
        cls = _load_plugin("pipe", name)
        if cls and not cls.internal and name != "core" and is_plugin_enabled("pipe", name):
            names.append(name)
    return names


def _mark_synced(pipe_name: str) -> None:
    from app.db import update_synced_at

    try:
        update_synced_at("pipe", pipe_name)
    except Exception:
        logging.getLogger(__name__).exception("Failed to update synced_at for %s", pipe_name)


def _run_pipe_sync(
    ep_name: str,
    pipe: Pipe,
    full_refresh: bool,
) -> Iterator[str]:
    """Run a single pipe's sync command, yielding SSE events."""
    log.info("Sync started: %s", ep_name)
    yield _sse_event("progress", {"pipe": ep_name, "message": "starting sync"})

    try:
        pipe.sync(full_refresh=full_refresh)
        _mark_synced(ep_name)
        log.info("Sync complete: %s", ep_name)
        yield _sse_event("complete", {"pipe": ep_name, "message": "done"})
    except Exception as exc:
        log.exception("Sync failed: %s", ep_name)
        yield _sse_event("error", {"pipe": ep_name, "message": str(exc)})


@router.post("")
def sync_all() -> StreamingResponse:
    def _stream() -> Iterator[str]:
        failed = []
        for name in _installed_pipe_names():
            if not acquire_sync_lock(name):
                yield _sse_event("progress", {"pipe": name, "message": "skipping: sync already in progress"})
                continue
            try:
                pipe = _load_pipe(name)
                yield from _run_pipe_sync(name, pipe, full_refresh=False)
            except Exception as exc:
                yield _sse_event("error", {"pipe": name, "message": str(exc)})
                failed.append(name)
            finally:
                release_sync_lock(name)

        if failed:
            yield _sse_event("error", {"message": f"Failed: {', '.join(failed)}"})
        else:
            yield _sse_event("complete", {"message": "all syncs complete"})

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/{name}")
def sync_pipe(name: str, body: SyncRequest | None = None) -> StreamingResponse:
    body = body or SyncRequest()

    # Verify the pipe is installed
    if name not in _installed_pipe_names():
        raise HTTPException(status_code=404, detail=f"Pipe not found: {name}")

    # Acquire lock before starting the stream so callers get HTTP 409, not an SSE error
    if not acquire_sync_lock(name):
        raise HTTPException(status_code=409, detail="Sync already in progress")

    def _stream() -> Iterator[str]:
        try:
            pipe = _load_pipe(name)
            yield from _run_pipe_sync(name, pipe, body.full_refresh)
        except Exception as exc:
            yield _sse_event("error", {"pipe": name, "message": str(exc)})
        finally:
            release_sync_lock(name)

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.get("/schedule")
def get_sync_schedule() -> list[ScheduleInfo]:
    """Return schedule status for all pipes with a sync frequency configured."""
    from app.db import get_all_sync_schedules

    return [ScheduleInfo(**row) for row in get_all_sync_schedules()]
