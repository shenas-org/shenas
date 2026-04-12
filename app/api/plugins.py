"""Plugin SSE streaming endpoints for install/remove."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import InstallRequest  # noqa: TC001
from shenas_plugins.core.plugin import (
    DEFAULT_INDEX,
    PUBLIC_KEY_PATH,
    VALID_KINDS,
    Plugin,
    PluginInstance,
    _load_public_key,
    _python_executable,
    _verify_from_index,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

router = APIRouter(prefix="/plugins", tags=["plugins"])

log = logging.getLogger(f"shenas.{__name__}")


def _validate_kind(kind: str) -> None:
    if kind not in VALID_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid kind: {kind}. Must be one of: {', '.join(sorted(VALID_KINDS))}",
        )


def _sse(event: str, **kwargs: Any) -> str:
    from app.jobs import get_job_id

    jid = get_job_id()
    if jid is not None and "job_id" not in kwargs:
        kwargs["job_id"] = jid
    return f"data: {json.dumps({'event': event, **kwargs})}\n\n"


def _run_subprocess(cmd: list[str]) -> Any:
    import subprocess

    return subprocess.run(cmd, capture_output=True, text=True)


async def _install_stream(name: str, kind: str, skip_verify: bool = False) -> AsyncIterator[str]:
    cls = Plugin.load_by_name_and_kind(name, kind)
    if (cls and cls.internal) or name == "core":
        yield _sse("done", ok=False, message=f"shenas-{kind}-{name} is an internal plugin")
        return

    pkg = Plugin.pkg(kind, name)
    display = name.replace("-", " ").title()
    kind_label = kind.title()

    if not skip_verify:
        yield _sse("log", text=f"Verifying signature for {pkg}...")
        if not PUBLIC_KEY_PATH.exists():
            yield _sse("done", ok=False, message=f"Public key not found at {PUBLIC_KEY_PATH}")
            return
        pub_key = _load_public_key(PUBLIC_KEY_PATH)
        error = _verify_from_index(pkg, DEFAULT_INDEX, pub_key)
        if error:
            yield _sse("done", ok=False, message=error)
            return
        yield _sse("log", text="Signature verified")

    import asyncio

    yield _sse("log", text=f"Installing {pkg}...")
    result = await asyncio.to_thread(
        _run_subprocess,
        [
            "uv",
            "pip",
            "install",
            pkg,
            "--index-url",
            f"{DEFAULT_INDEX}/simple/",
            "--extra-index-url",
            "https://pypi.org/simple/",
            "--python",
            _python_executable(),
        ],
    )

    for line in result.stderr.strip().splitlines():
        if line.strip():
            yield _sse("log", text=line.strip())

    if result.returncode == 0:
        Plugin.clear_caches()
        Plugin.load_by_name_and_kind(name, kind) or Plugin._load_fresh(kind, name)
        PluginInstance.get_or_create(kind, name, enabled=True)
        yield _sse("done", ok=True, message=f"Added {display} {kind_label}")
    else:
        yield _sse("done", ok=False, message=result.stderr.strip() or f"Failed to add {pkg}")


async def _remove_stream(name: str, kind: str) -> AsyncIterator[str]:
    cls = Plugin.load_by_name_and_kind(name, kind)
    if (cls and cls.internal) or name == "core":
        yield _sse("done", ok=False, message=f"shenas-{kind}-{name} is an internal plugin")
        return

    record = PluginInstance.find(kind, name)
    if record:
        record.delete()

    pkg = Plugin.pkg(kind, name)
    display = name.replace("-", " ").title()
    kind_label = kind.title()

    import asyncio

    yield _sse("log", text=f"Removing {pkg}...")
    result = await asyncio.to_thread(
        _run_subprocess,
        ["uv", "pip", "uninstall", pkg, "--python", _python_executable()],
    )

    for line in result.stderr.strip().splitlines():
        if line.strip():
            yield _sse("log", text=line.strip())

    if result.returncode == 0:
        Plugin.clear_caches()
        yield _sse("done", ok=True, message=f"Removed {display} {kind_label}")
    else:
        yield _sse("done", ok=False, message=result.stderr.strip() or f"Failed to remove {pkg}")


@router.post("/{kind}/install-stream")
async def install_stream(kind: str, body: InstallRequest) -> StreamingResponse:
    from app.jobs import bind_job_id, new_job_id

    _validate_kind(kind)
    name = body.names[0] if body.names else ""
    if not name:
        raise HTTPException(status_code=400, detail="No plugin name provided")

    async def _wrapped() -> AsyncIterator[str]:
        with bind_job_id(new_job_id()):
            async for chunk in _install_stream(name, kind, skip_verify=body.skip_verify):
                yield chunk

    return StreamingResponse(_wrapped(), media_type="text/event-stream")


@router.post("/{kind}/{name}/remove-stream")
async def remove_stream(kind: str, name: str) -> StreamingResponse:
    from app.jobs import bind_job_id, new_job_id

    _validate_kind(kind)

    async def _wrapped() -> AsyncIterator[str]:
        with bind_job_id(new_job_id()):
            async for chunk in _remove_stream(name, kind):
                yield chunk

    return StreamingResponse(_wrapped(), media_type="text/event-stream")
