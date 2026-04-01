"""Pub/sub dispatcher for real-time telemetry events."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

log = logging.getLogger("shenas.telemetry.dispatcher")

_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_lock = threading.Lock()
_loop: asyncio.AbstractEventLoop | None = None


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Set the asyncio event loop for cross-thread dispatching."""
    global _loop
    _loop = loop


def subscribe() -> asyncio.Queue[dict[str, Any]]:
    """Create a new subscriber queue."""
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
    with _lock:
        _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    """Remove a subscriber queue."""
    with _lock:
        _subscribers.discard(q)


def notify(event_type: str, data: list[dict[str, Any]]) -> None:
    """Notify all subscribers of new telemetry data. Thread-safe."""
    if not _subscribers or not data:
        return
    event = {"type": event_type, "data": data}
    with _lock:
        for q in list(_subscribers):
            if _loop and _loop.is_running():
                _loop.call_soon_threadsafe(_put_nowait, q, event)
            else:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    pass


def _put_nowait(q: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:
        pass
