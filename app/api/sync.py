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
from app.models import SyncRequest

if TYPE_CHECKING:
    from collections.abc import Iterator


router = APIRouter(prefix="/sync", tags=["sync"])

log = logging.getLogger(f"shenas.{__name__}")

SOURCE_PREFIX = "shenas-source-"


def _sse_event(event: str, data: dict[str, str]) -> str:
    from app.jobs import get_job_id

    jid = get_job_id()
    if jid is not None and "job_id" not in data:
        data = {**data, "job_id": jid}
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


def _sync_to_sse(source: Source, *, full_refresh: bool) -> Iterator[str]:
    """Wrap Source.run_sync_stream as SSE events."""
    for event, message in source.run_sync_stream(full_refresh=full_refresh):
        yield _sse_event(event, {"source": source.name, "message": message})


@router.post("")
def sync_all() -> StreamingResponse:
    from app.jobs import bind_job_id, new_job_id

    def _stream() -> Iterator[str]:
        # One job_id covers the whole sync-all run so every per-source event and
        # every Python log emitted during it can be correlated.
        with bind_job_id(new_job_id()):
            failed = []
            for name in _installed_source_names():
                try:
                    source = _load_source(name)
                except Exception as exc:
                    yield _sse_event("error", {"source": name, "message": str(exc)})
                    failed.append(name)
                    continue

                if not source.acquire_sync_lock():
                    yield _sse_event("progress", {"source": name, "message": "skipping: sync already in progress"})
                    continue
                try:
                    yield from _sync_to_sse(source, full_refresh=False)
                except Exception as exc:
                    yield _sse_event("error", {"source": name, "message": str(exc)})
                    failed.append(name)
                finally:
                    source.release_sync_lock()

            if failed:
                yield _sse_event("error", {"message": f"Failed: {', '.join(failed)}"})
            else:
                yield _sse_event("complete", {"message": "all syncs complete"})

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/{name}")
def sync_source(name: str, body: SyncRequest | None = None) -> StreamingResponse:
    from app.jobs import bind_job_id, new_job_id

    body = body or SyncRequest()

    if name not in _installed_source_names():
        raise HTTPException(status_code=404, detail=f"Source not found: {name}")

    source = _load_source(name)

    if not source.acquire_sync_lock():
        raise HTTPException(status_code=409, detail="Sync already in progress")

    def _stream() -> Iterator[str]:
        # bind_job_id must be inside the generator body, not around the
        # StreamingResponse(...) construction, because Starlette iterates the
        # generator after the route function returns.
        with bind_job_id(new_job_id()):
            try:
                yield from _sync_to_sse(source, full_refresh=body.full_refresh)
            except Exception as exc:
                yield _sse_event("error", {"source": name, "message": str(exc)})
            finally:
                source.release_sync_lock()

    return StreamingResponse(_stream(), media_type="text/event-stream")
