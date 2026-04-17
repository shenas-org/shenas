"""Embedded sync scheduler -- runs as a background asyncio task.

Replaces the standalone ``shenas-scheduler`` sidecar. Polls installed
sources for due syncs and triggers them directly (no HTTP round-trips).
Runs transforms after each successful sync.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shenas_sources.core.source import Source

log = logging.getLogger("shenas.scheduler")


async def run_sync_scheduler(check_interval: int = 60) -> None:
    """Background task: poll for due sources and sync them.

    Runs forever until cancelled. Errors in individual syncs are logged
    but don't stop the loop.
    """
    log.info("Sync scheduler started (interval: %ds)", check_interval)
    while True:
        try:
            _tick()
        except Exception:
            log.exception("Sync scheduler tick failed")
        await asyncio.sleep(check_interval)


def _tick() -> None:
    """Check all sources and sync any that are due."""
    from shenas_sources.core.source import Source as SourceCls

    for source_cls in SourceCls.load_all(include_internal=False):
        src = source_cls()
        if not src.is_due_for_sync:
            continue
        log.info("Source %s is due for sync", src.name)
        _run_sync(src)


def _run_sync(src: Source) -> None:
    """Run a single source sync + transforms."""
    if not src.acquire_sync_lock():
        log.debug("Skipping %s: sync already in progress", src.name)
        return
    try:
        for event in src.run_sync_stream():
            event_type = event.get("event", "progress") if isinstance(event, dict) else "progress"
            message = event.get("message", str(event)) if isinstance(event, dict) else str(event)
            if event_type == "error":
                log.error("Sync %s: %s", src.name, message)
            elif event_type == "complete":
                log.info("Sync %s complete: %s", src.name, message)
            else:
                log.debug("Sync %s: %s", src.name, message)

        # Run transforms after successful sync
        try:
            from shenas_transformers.core.transform import Transform

            count = Transform.run_for_source(src.name)
            if count:
                log.info("Ran %d transform(s) for %s", count, src.name)
        except Exception:
            log.exception("Transforms failed for %s", src.name)
    except Exception:
        log.exception("Sync %s failed", src.name)
    finally:
        src.release_sync_lock()
