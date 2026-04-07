"""Tests for the Table ABC + kind base classes."""

from __future__ import annotations

from typing import Annotated, Any, ClassVar

import pytest

from shenas_plugins.core.field import Field
from shenas_sources.core.table import (
    AggregateTable,
    CounterTable,
    DimensionTable,
    EventTable,
    IntervalTable,
    SnapshotTable,
)


class _Sample(EventTable):
    """A simple event table used by multiple tests."""

    name: ClassVar[str] = "sample"
    display_name: ClassVar[str] = "Sample Events"
    description: ClassVar[str | None] = "A sample event table for tests."
    pk: ClassVar[tuple[str, ...]] = ("id",)
    time_at: ClassVar[str] = "occurred_at"

    id: Annotated[int, Field(db_type="BIGINT", description="row id")]
    occurred_at: Annotated[str, Field(db_type="TIMESTAMP", description="when")]
    payload: Annotated[str | None, Field(db_type="VARCHAR", description="data")] = None

    @classmethod
    def extract(cls, client: Any, **_context: Any) -> Any:
        yield from client.get_rows()


class TestSubclassAutoDataclass:
    def test_field_annotations_become_dataclass(self) -> None:
        import dataclasses

        names = {f.name for f in dataclasses.fields(_Sample)}
        assert names == {"id", "occurred_at", "payload"}

    def test_can_construct_with_field_values(self) -> None:
        row = _Sample(id=1, occurred_at="2026-04-07T12:00:00Z", payload="hi")
        assert row.id == 1
        assert row.payload == "hi"

    def test_kind_inferred_from_base(self) -> None:
        assert _Sample.kind == "event"


class TestValidation:
    def test_missing_name_raises(self) -> None:
        with pytest.raises(TypeError, match="missing required class attribute `name`"):

            class _BadNoName(EventTable):
                display_name: ClassVar[str] = "x"
                pk: ClassVar[tuple[str, ...]] = ("id",)
                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_missing_display_name_raises(self) -> None:
        with pytest.raises(TypeError, match="missing required class attribute `display_name`"):

            class _BadNoDisplayName(EventTable):
                name: ClassVar[str] = "x"
                pk: ClassVar[tuple[str, ...]] = ("id",)
                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_missing_pk_raises(self) -> None:
        with pytest.raises(TypeError, match="missing required class attribute `pk`"):

            class _BadNoPk(EventTable):
                name: ClassVar[str] = "x"
                display_name: ClassVar[str] = "X"
                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_interval_requires_time_start_and_end(self) -> None:
        with pytest.raises(TypeError, match="IntervalTable requires both `time_start` and `time_end`"):

            class _BadInterval(IntervalTable):
                name: ClassVar[str] = "x"
                display_name: ClassVar[str] = "X"
                pk: ClassVar[tuple[str, ...]] = ("id",)
                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_counter_requires_counter_columns(self) -> None:
        with pytest.raises(TypeError, match="CounterTable requires `counter_columns`"):

            class _BadCounter(CounterTable):
                name: ClassVar[str] = "x"
                display_name: ClassVar[str] = "X"
                pk: ClassVar[tuple[str, ...]] = ("id",)
                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_valid_interval_passes(self) -> None:
        class _GoodInterval(IntervalTable):
            name: ClassVar[str] = "intervals"
            display_name: ClassVar[str] = "Intervals"
            pk: ClassVar[tuple[str, ...]] = ("id",)
            time_start: ClassVar[str] = "starts_at"
            time_end: ClassVar[str] = "ends_at"

            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            starts_at: Annotated[str, Field(db_type="TIMESTAMP", description="x")]
            ends_at: Annotated[str, Field(db_type="TIMESTAMP", description="x")]

        assert _GoodInterval.kind == "interval"

    def test_valid_counter_passes(self) -> None:
        class _GoodCounter(CounterTable):
            name: ClassVar[str] = "ctr"
            display_name: ClassVar[str] = "Ctr"
            pk: ClassVar[tuple[str, ...]] = ("id",)
            counter_columns: ClassVar[tuple[str, ...]] = ("distance_m",)
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            distance_m: Annotated[float, Field(db_type="DOUBLE", description="cum")] = 0.0

        assert _GoodCounter.kind == "counter"


class TestWriteDisposition:
    def test_event_is_merge(self) -> None:
        assert _Sample.write_disposition() == "merge"

    def test_dimension_is_scd2(self) -> None:
        class _Dim(DimensionTable):
            name: ClassVar[str] = "dim"
            display_name: ClassVar[str] = "Dim"
            pk: ClassVar[tuple[str, ...]] = ("id",)
            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        assert _Dim.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
        assert _Dim.kind == "dimension"

    def test_snapshot_is_scd2(self) -> None:
        class _Snap(SnapshotTable):
            name: ClassVar[str] = "snap"
            display_name: ClassVar[str] = "Snap"
            pk: ClassVar[tuple[str, ...]] = ("id",)
            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        assert _Snap.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
        assert _Snap.kind == "snapshot"

    def test_counter_is_append(self) -> None:
        class _Counter(CounterTable):
            name: ClassVar[str] = "ctr2"
            display_name: ClassVar[str] = "Ctr2"
            pk: ClassVar[tuple[str, ...]] = ("id",)
            counter_columns: ClassVar[tuple[str, ...]] = ("distance_m",)
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            distance_m: Annotated[float, Field(db_type="DOUBLE", description="cum")] = 0.0

        assert _Counter.write_disposition() == "append"
        assert _Counter.kind == "counter"

    def test_aggregate_is_merge(self) -> None:
        class _Agg(AggregateTable):
            name: ClassVar[str] = "agg"
            display_name: ClassVar[str] = "Agg"
            pk: ClassVar[tuple[str, ...]] = ("date",)
            time_at: ClassVar[str] = "date"
            date: Annotated[str, Field(db_type="DATE", description="x")]

        assert _Agg.write_disposition() == "merge"
        assert _Agg.kind == "aggregate"


class TestColumns:
    def test_columns_match_dataclass(self) -> None:
        cols = _Sample.to_dlt_columns()
        assert set(cols.keys()) >= {"id", "occurred_at", "payload"}
        assert cols["id"]["data_type"] == "bigint"
        assert cols["occurred_at"]["data_type"] == "timestamp"

    def test_observed_at_injected_when_no_time_at(self) -> None:
        class _NoTime(EventTable):
            name: ClassVar[str] = "nt"
            display_name: ClassVar[str] = "NT"
            pk: ClassVar[tuple[str, ...]] = ("activity_id", "athlete_id")
            # time_at omitted -- no native timestamp
            activity_id: Annotated[int, Field(db_type="BIGINT", description="x")]
            athlete_id: Annotated[int, Field(db_type="BIGINT", description="x")]

        cols = _NoTime.to_dlt_columns()
        assert "observed_at" in cols
        assert cols["observed_at"]["data_type"] == "timestamp"

    def test_observed_at_not_injected_when_time_at_set(self) -> None:
        cols = _Sample.to_dlt_columns()
        assert "observed_at" not in cols

    def test_counter_always_injects_observed_at(self) -> None:
        class _Counter(CounterTable):
            name: ClassVar[str] = "ctr3"
            display_name: ClassVar[str] = "Ctr3"
            pk: ClassVar[tuple[str, ...]] = ("id",)
            counter_columns: ClassVar[tuple[str, ...]] = ("dist",)
            id: Annotated[str, Field(db_type="VARCHAR", description="x")]
            dist: Annotated[float, Field(db_type="DOUBLE", description="x")] = 0.0

        cols = _Counter.to_dlt_columns()
        assert "observed_at" in cols


class TestToResource:
    def test_yields_extracted_rows(self) -> None:
        from unittest.mock import MagicMock

        client = MagicMock()
        client.get_rows.return_value = [
            {"id": 1, "occurred_at": "2026-04-07T12:00:00Z", "payload": "a"},
            {"id": 2, "occurred_at": "2026-04-07T13:00:00Z", "payload": "b"},
        ]
        rows = list(_Sample.to_resource(client))
        assert len(rows) == 2
        assert rows[0]["id"] == 1

    def test_observed_at_auto_injected_into_yielded_rows(self) -> None:
        from unittest.mock import MagicMock

        class _NoTime(EventTable):
            name: ClassVar[str] = "nt2"
            display_name: ClassVar[str] = "NT2"
            pk: ClassVar[tuple[str, ...]] = ("link_id",)
            link_id: Annotated[int, Field(db_type="BIGINT", description="x")]

            @classmethod
            def extract(cls, client: Any, **_context: Any) -> Any:
                yield {"link_id": 1}
                yield {"link_id": 2}

        rows = list(_NoTime.to_resource(MagicMock()))
        assert len(rows) == 2
        for row in rows:
            assert "observed_at" in row
            assert row["observed_at"].startswith("20")

    # Cursor wiring (Table.cursor_column -> dlt.sources.incremental) is exercised
    # end-to-end by the lunchmoney integration test where it runs inside a real
    # dlt pipeline. dlt cursors require source-state context to iterate, so a
    # standalone unit test isn't feasible without setting up a full pipeline.

    def test_extract_passes_context_kwargs(self) -> None:
        from unittest.mock import MagicMock

        class _CtxTable(EventTable):
            name: ClassVar[str] = "ctx"
            display_name: ClassVar[str] = "Ctx"
            pk: ClassVar[tuple[str, ...]] = ("id",)
            time_at: ClassVar[str] = "ts"
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            ts: Annotated[str, Field(db_type="TIMESTAMP", description="x")]

            @classmethod
            def extract(cls, client: Any, **context: Any) -> Any:
                yield from context.get("prefetched", [])

        rows = list(
            _CtxTable.to_resource(
                MagicMock(),
                prefetched=[{"id": 1, "ts": "2026-04-07T12:00:00Z"}],
            )
        )
        assert rows == [{"id": 1, "ts": "2026-04-07T12:00:00Z"}]
