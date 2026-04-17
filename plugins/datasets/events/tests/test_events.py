"""Tests for the events schema plugin."""

from __future__ import annotations

from shenas_datasets.events import EventsSchema
from shenas_datasets.events.metrics import ALL_TABLES, Event


class TestSchema:
    def test_table_count(self) -> None:
        assert len(ALL_TABLES) == 1

    def test_table_names(self) -> None:
        assert Event._Meta.name == "events"

    def test_pk(self) -> None:
        assert Event._Meta.pk == ("source", "source_id")

    def test_schema_class(self) -> None:
        assert EventsSchema.name == "events"
        assert EventsSchema.display_name == "Events"
        assert EventsSchema.tables == ["events"]

    def test_generate_ddl(self) -> None:
        ddl = Event.to_ddl()
        assert "CREATE TABLE" in ddl
        assert "source" in ddl
        assert "start_at" in ddl

    def test_ensure_idempotent(self, db_con) -> None:
        EventsSchema.ensure()
        EventsSchema.ensure()
        tables = db_con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        assert ("events",) in tables

    def test_metadata(self) -> None:
        meta = EventsSchema.metadata()
        assert len(meta) == 1
        cols = meta[0]["columns"]
        names = [c["name"] for c in cols]
        assert "source" in names
        assert "start_at" in names
        assert "title" in names
