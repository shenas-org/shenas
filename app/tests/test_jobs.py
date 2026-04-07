"""Tests for app.jobs -- contextvar binding, log filter, id generation."""

from __future__ import annotations

import logging
import threading

from app import jobs


class TestNewJobId:
    def test_length(self) -> None:
        assert len(jobs.new_job_id()) == 16

    def test_unique(self) -> None:
        ids = {jobs.new_job_id() for _ in range(100)}
        assert len(ids) == 100


class TestBindJobId:
    def test_outside_context_returns_none(self) -> None:
        assert jobs.get_job_id() is None

    def test_binds_for_with_block(self) -> None:
        with jobs.bind_job_id("abc"):
            assert jobs.get_job_id() == "abc"
        assert jobs.get_job_id() is None

    def test_nested_bindings_restore_previous(self) -> None:
        with jobs.bind_job_id("outer"):
            assert jobs.get_job_id() == "outer"
            with jobs.bind_job_id("inner"):
                assert jobs.get_job_id() == "inner"
            assert jobs.get_job_id() == "outer"
        assert jobs.get_job_id() is None

    def test_thread_does_not_inherit(self) -> None:
        seen: list[str | None] = []

        def _worker() -> None:
            seen.append(jobs.get_job_id())

        with jobs.bind_job_id("parent"):
            t = threading.Thread(target=_worker)
            t.start()
            t.join()

        # ContextVars don't propagate across raw threading.Thread boundaries.
        assert seen == [None]

    def test_thread_can_rebind(self) -> None:
        seen: list[str | None] = []

        def _worker(captured: str | None) -> None:
            with jobs.bind_job_id(captured):
                seen.append(jobs.get_job_id())

        with jobs.bind_job_id("from-parent"):
            captured = jobs.get_job_id()
            t = threading.Thread(target=_worker, args=(captured,))
            t.start()
            t.join()

        assert seen == ["from-parent"]


class TestJobIdLogFilter:
    def test_injects_current_job_id_into_record(self) -> None:
        f = jobs.JobIdLogFilter()
        record = logging.LogRecord("x", logging.INFO, "f.py", 1, "msg", None, None)
        with jobs.bind_job_id("job-123"):
            assert f.filter(record) is True
        assert record.job_id == "job-123"

    def test_injects_none_when_no_binding(self) -> None:
        f = jobs.JobIdLogFilter()
        record = logging.LogRecord("x", logging.INFO, "f.py", 1, "msg", None, None)
        assert f.filter(record) is True
        assert record.job_id is None
