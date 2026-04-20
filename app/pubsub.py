"""In-process async pub/sub for GraphQL subscription topics.

Lightweight broker that lets mutations and sync hooks publish
data-change notifications, which GraphQL subscription resolvers
yield to connected clients.

Usage::

    from app.pubsub import pubsub

    # Publishing (from sync code or mutations):
    pubsub.publish_sync("entity_changed", {"uuid": "abc", "type": "human", "name": "Alice"})

    # Subscribing (from async subscription resolver):
    async for event in pubsub.subscribe("entity_changed"):
        yield EntityChangedPayload(**event)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator  # noqa: TC003 -- runtime: used as return type in subscribe()
from typing import Any

log = logging.getLogger("shenas.pubsub")

_MAX_QUEUE_SIZE = 256


class PubSub:
    """Topic-based in-process pub/sub.

    Thread-safe for publishing (``publish_sync``); async-safe for
    subscribing. Each subscriber gets its own queue so slow consumers
    don't block fast ones.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
        return self._loop

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish an event to all subscribers of ``topic``."""
        subscribers = self._subscribers.get(topic, [])
        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                log.warning("PubSub: dropped event on topic %s (queue full)", topic)

    def publish_sync(self, topic: str, payload: dict[str, Any]) -> None:
        """Thread-safe publish for non-async code (sync hooks, mutations).

        Schedules the publish onto the event loop. If no loop is running
        (e.g. during tests), publishes directly to queues.
        """
        subscribers = self._subscribers.get(topic, [])
        if not subscribers:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(self._deliver, topic, payload)
        except RuntimeError:
            # No running loop -- deliver directly (tests, CLI)
            self._deliver(topic, payload)

    def _deliver(self, topic: str, payload: dict[str, Any]) -> None:
        for queue in self._subscribers.get(topic, []):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                log.warning("PubSub: dropped event on topic %s (queue full)", topic)

    async def subscribe(self, topic: str) -> AsyncIterator[dict[str, Any]]:
        """Yield events for ``topic`` as they arrive.

        Creates a per-subscriber queue that is cleaned up when the
        caller stops iterating (e.g. client disconnects).
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
        self._subscribers.setdefault(topic, []).append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.get(topic, []).remove(queue)


# Module-level singleton
pubsub = PubSub()
