"""Tests for the on_progress callback in run_sync."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _stub_dlt() -> tuple[MagicMock, MagicMock]:
    """Build a fake dlt pipeline that returns a fake load info synchronously."""
    fake_pipeline = MagicMock()
    fake_pipeline.run.return_value = SimpleNamespace(load_packages=[])
    fake_dlt = MagicMock()
    fake_dlt.pipeline.return_value = fake_pipeline
    return fake_dlt, fake_pipeline


def test_on_progress_called_at_each_checkpoint() -> None:
    from shenas_sources.core import cli

    fake_dlt, _ = _stub_dlt()
    fake_dest, fake_mem_con = MagicMock(), MagicMock()
    r1 = SimpleNamespace(name="r1")
    r2 = SimpleNamespace(name="r2")

    progress: list[tuple[str, str]] = []

    def transform_fn() -> None:
        return None

    with (
        patch.dict("sys.modules", {"dlt": fake_dlt}),
        patch("shenas_sources.core.db.dlt_destination", return_value=(fake_dest, fake_mem_con)),
        patch("shenas_sources.core.db.flush_to_encrypted"),
        patch("shenas_sources.core.db.DB_PATH") as db_path,
    ):
        db_path.parent.mkdir = MagicMock()
        cli.run_sync(
            "garmin",
            "garmin",
            [r1, r2],
            full_refresh=False,
            transform_fn=transform_fn,
            on_progress=lambda e, m: progress.append((e, m)),
        )

    # Each resource produces a single fetch_start checkpoint -- fetch_done and
    # flush were intentionally omitted from the on_progress stream because they
    # showed up as duplicate bare resource names in the job panel.
    assert ("fetch_start", "Fetching (1/2): r1") in progress
    assert ("fetch_start", "Fetching (2/2): r2") in progress
    assert ("transform_start", "Running transforms") in progress
    # And no fetch_done / flush noise:
    assert all(e != "fetch_done" for e, _ in progress)
    assert all(e != "flush" for e, _ in progress)


def test_on_progress_default_none_does_not_crash() -> None:
    """Backwards compat: callers that don't pass on_progress still work."""
    from shenas_sources.core import cli

    fake_dlt, _ = _stub_dlt()
    fake_dest, fake_mem_con = MagicMock(), MagicMock()
    r1 = SimpleNamespace(name="r1")

    with (
        patch.dict("sys.modules", {"dlt": fake_dlt}),
        patch("shenas_sources.core.db.dlt_destination", return_value=(fake_dest, fake_mem_con)),
        patch("shenas_sources.core.db.flush_to_encrypted"),
        patch("shenas_sources.core.db.DB_PATH") as db_path,
    ):
        db_path.parent.mkdir = MagicMock()
        cli.run_sync("garmin", "garmin", [r1])  # no on_progress
