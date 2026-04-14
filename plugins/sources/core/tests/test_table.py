"""Tests for the Table ABC + kind base classes."""

from __future__ import annotations

from typing import Annotated, Any, ClassVar

import pytest

from app.table import Field
from shenas_sources.core.table import (
    AggregateTable,
    CounterTable,
    DimensionTable,
    EventTable,
    IntervalTable,
    M2MTable,
    SnapshotTable,
)


class TestM2MTable:
    def test_kind_and_disposition(self) -> None:
        class _Link(M2MTable):
            class _Meta:
                name = "links"
                display_name = "Links"
                pk = ("a_id", "b_id")

            a_id: Annotated[int, Field(db_type="BIGINT", description="x")]
            b_id: Annotated[int, Field(db_type="BIGINT", description="x")]

        assert issubclass(_Link, M2MTable)
        assert _Link.write_disposition() == {"disposition": "merge", "strategy": "scd2"}

    def test_requires_composite_pk(self) -> None:
        with pytest.raises(TypeError, match="M2MTable requires a composite PK"):

            class _BadLink(M2MTable):
                class _Meta:
                    name = "x"
                    display_name = "X"
                    pk = ("only_one",)

                only_one: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_no_observed_at_injected(self) -> None:
        class _Link(M2MTable):
            class _Meta:
                name = "links2"
                display_name = "Links"
                pk = ("a_id", "b_id")

            a_id: Annotated[int, Field(db_type="BIGINT", description="x")]
            b_id: Annotated[int, Field(db_type="BIGINT", description="x")]

        cols = _Link.to_dlt_columns()
        assert "observed_at" not in cols
        assert set(cols.keys()) == {"a_id", "b_id"}


class _Sample(EventTable):
    """A simple event table used by multiple tests."""

    class _Meta:
        name = "sample"
        display_name = "Sample Events"
        description = "A sample event table for tests."
        pk = ("id",)

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
        row = _Sample(id=1, occurred_at="2026-04-07T12:00:00Z", payload="hi")  # ty: ignore[unknown-argument]
        assert row.id == 1
        assert row.payload == "hi"

    def test_kind_inferred_from_base(self) -> None:
        assert issubclass(_Sample, EventTable)


class TestValidation:
    def test_missing_name_raises(self) -> None:
        with pytest.raises(TypeError, match="_Meta missing required attribute `name`"):

            class _BadNoName(EventTable):
                class _Meta:
                    display_name = "x"
                    pk = ("id",)

                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_missing_display_name_raises(self) -> None:
        with pytest.raises(TypeError, match="_Meta missing required attribute `display_name`"):

            class _BadNoDisplayName(EventTable):
                class _Meta:
                    name = "x"
                    pk = ("id",)

                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_missing_pk_raises(self) -> None:
        with pytest.raises(TypeError, match="_Meta missing required attribute `pk`"):

            class _BadNoPk(EventTable):
                class _Meta:
                    name = "x"
                    display_name = "X"

                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_interval_requires_time_start_and_end(self) -> None:
        with pytest.raises(TypeError, match="IntervalTable requires both `time_start` and `time_end`"):

            class _BadInterval(IntervalTable):
                class _Meta:
                    name = "x"
                    display_name = "X"
                    pk = ("id",)

                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_counter_requires_counter_columns(self) -> None:
        with pytest.raises(TypeError, match="CounterTable requires `counter_columns`"):

            class _BadCounter(CounterTable):
                class _Meta:
                    name = "x"
                    display_name = "X"
                    pk = ("id",)

                id: Annotated[int, Field(db_type="BIGINT", description="x")]

    def test_valid_interval_passes(self) -> None:
        class _GoodInterval(IntervalTable):
            class _Meta:
                name = "intervals"
                display_name = "Intervals"
                pk = ("id",)

            time_start: ClassVar[str] = "starts_at"
            time_end: ClassVar[str] = "ends_at"

            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            starts_at: Annotated[str, Field(db_type="TIMESTAMP", description="x")]
            ends_at: Annotated[str, Field(db_type="TIMESTAMP", description="x")]

        assert issubclass(_GoodInterval, IntervalTable)

    def test_valid_counter_passes(self) -> None:
        class _GoodCounter(CounterTable):
            class _Meta:
                name = "ctr"
                display_name = "Ctr"
                pk = ("id",)

            counter_columns: ClassVar[tuple[str, ...]] = ("distance_m",)
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            distance_m: Annotated[float, Field(db_type="DOUBLE", description="cum")] = 0.0

        assert issubclass(_GoodCounter, CounterTable)


class TestWriteDisposition:
    def test_event_is_merge(self) -> None:
        assert _Sample.write_disposition() == "merge"

    def test_dimension_is_scd2(self) -> None:
        class _Dim(DimensionTable):
            class _Meta:
                name = "dim"
                display_name = "Dim"
                pk = ("id",)

            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        assert _Dim.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
        assert issubclass(_Dim, DimensionTable)

    def test_snapshot_is_scd2(self) -> None:
        class _Snap(SnapshotTable):
            class _Meta:
                name = "snap"
                display_name = "Snap"
                pk = ("id",)

            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        assert _Snap.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
        assert issubclass(_Snap, SnapshotTable)

    def test_counter_is_append(self) -> None:
        class _Counter(CounterTable):
            class _Meta:
                name = "ctr2"
                display_name = "Ctr2"
                pk = ("id",)

            counter_columns: ClassVar[tuple[str, ...]] = ("distance_m",)
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            distance_m: Annotated[float, Field(db_type="DOUBLE", description="cum")] = 0.0

        assert _Counter.write_disposition() == "append"
        assert issubclass(_Counter, CounterTable)

    def test_aggregate_is_merge(self) -> None:
        class _Agg(AggregateTable):
            class _Meta:
                name = "agg"
                display_name = "Agg"
                pk = ("date",)

            time_at: ClassVar[str] = "date"
            date: Annotated[str, Field(db_type="DATE", description="x")]

        assert _Agg.write_disposition() == "merge"
        assert issubclass(_Agg, AggregateTable)


class TestColumns:
    def test_columns_match_dataclass(self) -> None:
        cols = _Sample.to_dlt_columns()
        assert set(cols.keys()) >= {"id", "occurred_at", "payload"}
        assert cols["id"]["data_type"] == "bigint"
        assert cols["occurred_at"]["data_type"] == "timestamp"

    def test_observed_at_injected_when_no_time_at(self) -> None:
        class _NoTime(EventTable):
            class _Meta:
                name = "nt"
                display_name = "NT"
                pk = ("activity_id", "athlete_id")

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
            class _Meta:
                name = "ctr3"
                display_name = "Ctr3"
                pk = ("id",)

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
            class _Meta:
                name = "nt2"
                display_name = "NT2"
                pk = ("link_id",)

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
            class _Meta:
                name = "ctx"
                display_name = "Ctx"
                pk = ("id",)

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


class TestTableKindAndMetadata:
    """Tests for the kind-aware extensions to ``Table.table_metadata()``."""

    def test_kind_event_with_time_at(self) -> None:
        class _Evt(EventTable):
            class _Meta:
                name = "evts"
                display_name = "Events"
                pk = ("id",)

            time_at: ClassVar[str] = "ts"
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            ts: Annotated[str, Field(db_type="TIMESTAMP", description="x")]

        assert _Evt.table_kind() == "event"
        meta = _Evt.table_metadata()
        assert meta["kind"] == "event"
        assert meta["time_columns"] == {"time_at": "ts"}
        assert "as_of_macro" not in meta
        assert "Filter or window by `time_at`" in meta["query_hint"]

    def test_kind_event_with_observed_at_injected(self) -> None:
        class _Evt(EventTable):
            class _Meta:
                name = "evts_no_ts"
                display_name = "Events without time"
                pk = ("id",)

            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        meta = _Evt.table_metadata()
        assert meta["kind"] == "event"
        # Without time_at, EventTable._needs_observed_at() is True -> the loader
        # auto-injects an observed_at column. The catalog should advertise that.
        assert meta["time_columns"]["observed_at_injected"] is True

    def test_kind_interval_emits_both_time_columns(self) -> None:
        class _Iv(IntervalTable):
            class _Meta:
                name = "intervals"
                display_name = "Intervals"
                pk = ("id",)

            time_start: ClassVar[str] = "starts_at"
            time_end: ClassVar[str] = "ends_at"
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            starts_at: Annotated[str, Field(db_type="TIMESTAMP", description="x")]
            ends_at: Annotated[str, Field(db_type="TIMESTAMP", description="x")]

        meta = _Iv.table_metadata()
        assert meta["kind"] == "interval"
        assert meta["time_columns"]["time_start"] == "starts_at"
        assert meta["time_columns"]["time_end"] == "ends_at"
        assert "overlap" in meta["query_hint"].lower()

    def test_kind_dimension_has_as_of_macro(self) -> None:
        class _Dim(DimensionTable):
            class _Meta:
                name = "dims"
                display_name = "Dims"
                schema = "mysrc"
                pk = ("id",)

            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        meta = _Dim.table_metadata()
        assert meta["kind"] == "dimension"
        assert meta["as_of_macro"] == "mysrc.dims_as_of"
        assert "AS-OF" in meta["query_hint"]

    def test_kind_snapshot_has_as_of_macro(self) -> None:
        class _Snap(SnapshotTable):
            class _Meta:
                name = "snap"
                display_name = "Snapshot"
                schema = "mysrc"
                pk = ("id",)

            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        meta = _Snap.table_metadata()
        assert meta["kind"] == "snapshot"
        assert meta["as_of_macro"] == "mysrc.snap_as_of"

    def test_kind_m2m_has_as_of_macro(self) -> None:
        class _Link(M2MTable):
            class _Meta:
                name = "links"
                display_name = "Links"
                schema = "mysrc"
                pk = ("a_id", "b_id")

            a_id: Annotated[int, Field(db_type="BIGINT", description="x")]
            b_id: Annotated[int, Field(db_type="BIGINT", description="x")]

        meta = _Link.table_metadata()
        assert meta["kind"] == "m2m_relation"
        assert meta["as_of_macro"] == "mysrc.links_as_of"
        assert "linked at ts" in meta["query_hint"]

    def test_kind_aggregate_has_no_as_of_macro(self) -> None:
        class _Agg(AggregateTable):
            class _Meta:
                name = "rollup"
                display_name = "Rollup"
                schema = "mysrc"
                pk = ("date",)

            time_at: ClassVar[str] = "date"
            date: Annotated[str, Field(db_type="DATE", description="x")]

        meta = _Agg.table_metadata()
        assert meta["kind"] == "aggregate"
        assert "as_of_macro" not in meta
        assert meta["time_columns"] == {"time_at": "date"}

    def test_kind_counter_observed_at_injected(self) -> None:
        class _Ctr(CounterTable):
            class _Meta:
                name = "counters"
                display_name = "Counters"
                pk = ("id",)

            counter_columns: ClassVar[tuple[str, ...]] = ("distance_m",)
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            distance_m: Annotated[float, Field(db_type="DOUBLE", description="cum")] = 0.0

        meta = _Ctr.table_metadata()
        assert meta["kind"] == "counter"
        # Counters always inject observed_at.
        assert meta["time_columns"] == {"observed_at_injected": True}

    def test_cursor_column_emitted_when_set(self) -> None:
        class _Cursored(EventTable):
            class _Meta:
                name = "messages"
                display_name = "Messages"
                pk = ("id",)

            time_at: ClassVar[str] = "internal_date"
            cursor_column: ClassVar[str] = "internal_date"
            id: Annotated[str, Field(db_type="VARCHAR", description="x")]
            internal_date: Annotated[int, Field(db_type="BIGINT", description="x")]

        meta = _Cursored.table_metadata()
        assert meta["time_columns"]["time_at"] == "internal_date"
        assert meta["time_columns"]["cursor_column"] == "internal_date"

    def test_non_source_table_has_no_kind(self) -> None:
        # A bare Table subclass (not a SourceTable kind) should report
        # kind=None and have no kind-specific keys. This covers MetricTable
        # subclasses, system tables (Plugin._Table, Workspace._Table, ...),
        # and SourceConfig / SourceAuth.
        from app.table import Table

        class _Plain(Table):
            class _Meta:
                name = "plain"
                display_name = "Plain"
                pk = ("id",)

            id: Annotated[int, Field(db_type="BIGINT", description="x")]

        # table_kind / table_metadata now live on DataTable; a plain Table
        # subclass exposes only column_metadata() (no kind taxonomy).
        assert not hasattr(_Plain, "table_kind")
        assert not hasattr(_Plain, "table_metadata")
        columns = _Plain.column_metadata()
        assert [c["name"] for c in columns] == ["id"]

    def test_schema_field_present_for_all_tables(self) -> None:
        # The catalog needs the schema for every table so consumers can
        # qualify references. Read it back even when None.
        class _NoSchema(EventTable):
            class _Meta:
                name = "noschema"
                display_name = "No Schema"
                pk = ("id",)

            time_at: ClassVar[str] = "ts"
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            ts: Annotated[str, Field(db_type="TIMESTAMP", description="x")]

        meta = _NoSchema.table_metadata()
        assert meta["schema"] is None

        class _WithSchema(EventTable):
            class _Meta:
                name = "withschema"
                display_name = "With Schema"
                schema = "garmin"
                pk = ("id",)

            time_at: ClassVar[str] = "ts"
            id: Annotated[int, Field(db_type="BIGINT", description="x")]
            ts: Annotated[str, Field(db_type="TIMESTAMP", description="x")]

        meta = _WithSchema.table_metadata()
        assert meta["schema"] == "garmin"
