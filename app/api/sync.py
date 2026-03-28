"""Sync API endpoints with SSE streaming."""

import inspect
import json
from collections.abc import Iterator
from importlib.metadata import entry_points

import typer
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncRequest(BaseModel):
    start_date: str | None = None
    full_refresh: bool = False


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _run_pipe_sync(ep_name: str, pipe_app: typer.Typer, start_date: str | None, full_refresh: bool) -> Iterator[str]:
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

    try:
        sync_callback(**kwargs)
        yield _sse_event("complete", {"pipe": ep_name, "message": "done"})
    except SystemExit:
        yield _sse_event("complete", {"pipe": ep_name, "message": "done"})
    except Exception as exc:
        yield _sse_event("error", {"pipe": ep_name, "message": str(exc)})


@router.post("")
def sync_all() -> StreamingResponse:
    def _stream() -> Iterator[str]:
        failed = []
        for ep in sorted(entry_points(group="shenas.pipes"), key=lambda e: e.name):
            if ep.name == "core":
                continue
            try:
                pipe_app = ep.load()
                yield from _run_pipe_sync(ep.name, pipe_app, start_date=None, full_refresh=False)
            except Exception as exc:
                yield _sse_event("error", {"pipe": ep.name, "message": str(exc)})
                failed.append(ep.name)

        if failed:
            yield _sse_event("error", {"message": f"Failed: {', '.join(failed)}"})
        else:
            yield _sse_event("complete", {"message": "all syncs complete"})

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.post("/{name}")
def sync_pipe(name: str, body: SyncRequest | None = None) -> StreamingResponse:
    body = body or SyncRequest()

    # Find the pipe entry point
    matching = [ep for ep in entry_points(group="shenas.pipes") if ep.name == name]
    if not matching:
        raise HTTPException(status_code=404, detail=f"Pipe not found: {name}")

    ep = matching[0]

    def _stream() -> Iterator[str]:
        try:
            pipe_app = ep.load()
            yield from _run_pipe_sync(name, pipe_app, body.start_date, body.full_refresh)
        except Exception as exc:
            yield _sse_event("error", {"pipe": name, "message": str(exc)})

    return StreamingResponse(_stream(), media_type="text/event-stream")
