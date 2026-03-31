"""Sync API endpoints with SSE streaming."""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import subprocess
import sys
import threading
from collections.abc import Iterator

import typer
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import ScheduleInfo, SyncRequest

router = APIRouter(prefix="/sync", tags=["sync"])

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
        try:
            lock.release()
        except RuntimeError:
            pass


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
    from app.api.plugins import _is_internal
    from app.db import is_plugin_enabled

    return [
        p["name"].removeprefix(PIPE_PREFIX)
        for p in packages
        if p["name"].startswith(PIPE_PREFIX)
        and not _is_internal("pipe", p["name"].removeprefix(PIPE_PREFIX))
        and is_plugin_enabled("pipe", p["name"].removeprefix(PIPE_PREFIX))
    ]


def _load_pipe_app(name: str) -> typer.Typer:
    """Load a pipe's typer app by importing its CLI module directly."""
    module_name = f"shenas_pipes.{name}.cli"
    # Invalidate caches so packages installed after server start are found
    importlib.invalidate_caches()
    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError:
        # Module might be installed but the namespace package path is stale.
        # Refresh sys.path entries by re-importing the namespace package.
        import sys

        for key in list(sys.modules):
            if key == "shenas_pipes" or key.startswith("shenas_pipes."):
                del sys.modules[key]
        try:
            mod = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            msg = f"Cannot import {module_name}: {exc}. Ensure pipes are installed and server is running from the workspace."
            raise ImportError(msg) from exc
    return mod.app


def _mark_synced(pipe_name: str) -> None:
    from app.db import update_synced_at

    try:
        update_synced_at("pipe", pipe_name)
    except Exception:
        logging.getLogger(__name__).exception("Failed to update synced_at for %s", pipe_name)


def _run_pipe_sync(
    ep_name: str,
    pipe_app: typer.Typer,
    start_date: str | None,
    full_refresh: bool,
    extra: dict[str, str | int | bool] | None = None,
) -> Iterator[str]:
    """Run a single pipe's sync command, yielding SSE events."""
    yield _sse_event("progress", {"pipe": ep_name, "message": "starting sync"})

    sync_callback = None
    for cmd in pipe_app.registered_commands:
        cmd_name = cmd.name or (getattr(cmd.callback, "__name__", None) if cmd.callback else None)
        if cmd_name == "sync" and cmd.callback:
            sync_callback = cmd.callback
            break

    if not sync_callback:
        yield _sse_event("error", {"pipe": ep_name, "message": "no sync command found"})
        return

    kwargs = {}
    for p_name, p in inspect.signature(sync_callback).parameters.items():
        if isinstance(p.default, typer.models.OptionInfo):
            kwargs[p_name] = p.default.default

    if start_date and "start_date" in kwargs:
        kwargs["start_date"] = start_date
    if full_refresh and "full_refresh" in kwargs:
        kwargs["full_refresh"] = True
    # Pass extra options that match the callback's parameters
    if extra:
        for k, v in extra.items():
            if k in kwargs:
                kwargs[k] = v

    try:
        sync_callback(**kwargs)
        _mark_synced(ep_name)
        yield _sse_event("complete", {"pipe": ep_name, "message": "done"})
    except SystemExit as exc:
        if exc.code and exc.code != 0:
            yield _sse_event("error", {"pipe": ep_name, "message": f"Sync failed (exit code {exc.code}). Check server logs."})
        else:
            _mark_synced(ep_name)
            yield _sse_event("complete", {"pipe": ep_name, "message": "done"})
    except Exception as exc:
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
                pipe_app = _load_pipe_app(name)
                yield from _run_pipe_sync(name, pipe_app, start_date=None, full_refresh=False)
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
            pipe_app = _load_pipe_app(name)
            yield from _run_pipe_sync(name, pipe_app, body.start_date, body.full_refresh, body.extra)
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


