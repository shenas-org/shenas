"""Tests for the in-process async pub/sub broker."""

import asyncio

import pytest

from app.pubsub import PubSub


@pytest.fixture
def broker():
    return PubSub()


class TestPublishSync:
    def test_no_subscribers_is_noop(self, broker):
        broker.publish_sync("topic", {"key": "value"})

    def test_delivers_to_queue_without_event_loop(self, broker):
        queue = asyncio.Queue()
        broker._subscribers["topic"] = [queue]
        broker.publish_sync("topic", {"x": 1})
        assert not queue.empty()
        assert queue.get_nowait() == {"x": 1}

    def test_delivers_to_multiple_subscribers(self, broker):
        queue_a = asyncio.Queue()
        queue_b = asyncio.Queue()
        broker._subscribers["topic"] = [queue_a, queue_b]
        broker.publish_sync("topic", {"x": 1})
        assert queue_a.get_nowait() == {"x": 1}
        assert queue_b.get_nowait() == {"x": 1}

    def test_ignores_subscribers_on_other_topics(self, broker):
        queue = asyncio.Queue()
        broker._subscribers["other"] = [queue]
        broker.publish_sync("topic", {"x": 1})
        assert queue.empty()


class TestPublishAsync:
    def test_delivers_to_subscriber(self, broker):
        async def run():
            queue = asyncio.Queue()
            broker._subscribers["topic"] = [queue]
            await broker.publish("topic", {"event": "test"})
            assert queue.get_nowait() == {"event": "test"}

        asyncio.run(run())

    def test_drops_when_queue_full(self, broker):
        async def run():
            queue = asyncio.Queue(maxsize=1)
            broker._subscribers["topic"] = [queue]
            await broker.publish("topic", {"first": True})
            await broker.publish("topic", {"second": True})
            assert queue.qsize() == 1

        asyncio.run(run())


class TestSubscribe:
    def test_yields_published_events(self, broker):
        async def run():
            received = []

            async def consumer():
                async for event in broker.subscribe("topic"):
                    received.append(event)
                    if len(received) >= 2:
                        break

            task = asyncio.create_task(consumer())
            await asyncio.sleep(0.01)
            await broker.publish("topic", {"n": 1})
            await broker.publish("topic", {"n": 2})
            await task
            assert received == [{"n": 1}, {"n": 2}]

        asyncio.run(run())

    def test_cleans_up_on_cancel(self, broker):
        async def run():
            async def consumer():
                async for _ in broker.subscribe("topic"):
                    pass

            task = asyncio.create_task(consumer())
            await asyncio.sleep(0.01)
            assert len(broker._subscribers.get("topic", [])) == 1
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert len(broker._subscribers.get("topic", [])) == 0

        asyncio.run(run())

    def test_independent_subscribers(self, broker):
        async def run():
            received_a = []
            received_b = []

            async def consumer_a():
                async for event in broker.subscribe("topic"):
                    received_a.append(event)
                    if len(received_a) >= 1:
                        break

            async def consumer_b():
                async for event in broker.subscribe("topic"):
                    received_b.append(event)
                    if len(received_b) >= 1:
                        break

            task_a = asyncio.create_task(consumer_a())
            task_b = asyncio.create_task(consumer_b())
            await asyncio.sleep(0.01)
            await broker.publish("topic", {"shared": True})
            await task_a
            await task_b
            assert received_a == [{"shared": True}]
            assert received_b == [{"shared": True}]

        asyncio.run(run())


class TestDeliver:
    def test_deliver_to_full_queue_does_not_raise(self, broker):
        queue = asyncio.Queue(maxsize=1)
        queue.put_nowait({"old": True})
        broker._subscribers["topic"] = [queue]
        broker._deliver("topic", {"new": True})
        assert queue.qsize() == 1
