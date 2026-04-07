"""Tests for app.telemetry.dispatcher pub/sub."""

from __future__ import annotations

import asyncio

import pytest

from app.telemetry import dispatcher


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    dispatcher._subscribers.clear()
    dispatcher._loop = None


class TestSubscribeUnsubscribe:
    def test_subscribe_adds_queue(self) -> None:
        q = dispatcher.subscribe()
        assert q in dispatcher._subscribers

    def test_unsubscribe_removes_queue(self) -> None:
        q = dispatcher.subscribe()
        dispatcher.unsubscribe(q)
        assert q not in dispatcher._subscribers

    def test_unsubscribe_unknown_is_noop(self) -> None:
        q: asyncio.Queue = asyncio.Queue()
        dispatcher.unsubscribe(q)  # should not raise


class TestNotify:
    def test_no_subscribers_does_nothing(self) -> None:
        dispatcher.notify("metric", [{"x": 1}])  # should not raise

    def test_empty_data_does_nothing(self) -> None:
        q = dispatcher.subscribe()
        dispatcher.notify("metric", [])
        assert q.empty()

    def test_notifies_each_subscriber_inline(self) -> None:
        q1 = dispatcher.subscribe()
        q2 = dispatcher.subscribe()
        dispatcher.notify("metric", [{"x": 1}])
        evt1 = q1.get_nowait()
        evt2 = q2.get_nowait()
        assert evt1 == {"type": "metric", "data": [{"x": 1}]}
        assert evt2 == evt1

    def test_full_queue_drops_silently_inline(self) -> None:
        q = dispatcher.subscribe()
        # fill the queue
        for _ in range(q.maxsize):
            q.put_nowait({"type": "filler"})
        # this should not raise
        dispatcher.notify("metric", [{"x": 1}])
        assert q.qsize() == q.maxsize

    def test_notifies_via_loop_when_set(self) -> None:
        import threading

        loop = asyncio.new_event_loop()

        def _run_loop() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        t = threading.Thread(target=_run_loop, daemon=True)
        t.start()
        try:
            # Wait until the loop is actually running
            for _ in range(50):
                if loop.is_running():
                    break
                import time

                time.sleep(0.01)

            dispatcher.set_loop(loop)
            q: asyncio.Queue = asyncio.Queue(maxsize=10)
            with dispatcher._lock:
                dispatcher._subscribers.add(q)

            dispatcher.notify("metric", [{"x": 1}])

            # Drain via the loop
            future = asyncio.run_coroutine_threadsafe(asyncio.wait_for(q.get(), timeout=1.0), loop)
            evt = future.result(timeout=2.0)
            assert evt == {"type": "metric", "data": [{"x": 1}]}
        finally:
            loop.call_soon_threadsafe(loop.stop)
            t.join(timeout=2.0)
            loop.close()


class TestSetLoop:
    def test_assigns_loop(self) -> None:
        loop = asyncio.new_event_loop()
        dispatcher.set_loop(loop)
        assert dispatcher._loop is loop
        loop.close()
