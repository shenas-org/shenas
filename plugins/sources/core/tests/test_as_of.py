"""Tests for the AS-OF macro generator."""

from __future__ import annotations

import duckdb
import pytest

from shenas_sources.core.as_of import apply_as_of_macros, find_scd2_tables


@pytest.fixture
def con(tmp_path):
    db = tmp_path / "as_of_test.duckdb"
    c = duckdb.connect(str(db))
    c.execute("CREATE SCHEMA gcalendar")
    # SCD2 dimension table
    c.execute(
        """
        CREATE TABLE gcalendar.calendars (
            id VARCHAR,
            summary VARCHAR,
            _dlt_valid_from TIMESTAMP,
            _dlt_valid_to TIMESTAMP
        )
        """
    )
    c.execute(
        """
        INSERT INTO gcalendar.calendars VALUES
            ('c1', 'Work',    TIMESTAMP '2026-01-01 00:00:00', TIMESTAMP '2026-02-01 00:00:00'),
            ('c1', 'Day Job', TIMESTAMP '2026-02-01 00:00:00', NULL)
        """
    )
    # Non-SCD2 event table -- should be ignored
    c.execute("CREATE TABLE gcalendar.events (id VARCHAR, start_date TIMESTAMP)")
    c.execute("INSERT INTO gcalendar.events VALUES ('e1', TIMESTAMP '2026-01-15 09:00:00')")
    yield c
    c.close()


class TestFindScd2Tables:
    def test_finds_only_scd2_tables(self, con) -> None:
        assert find_scd2_tables(con, "gcalendar") == ["calendars"]

    def test_empty_schema(self, con) -> None:
        con.execute("CREATE SCHEMA empty_schema")
        assert find_scd2_tables(con, "empty_schema") == []


class TestApplyAsOfMacros:
    def test_creates_macro_per_scd2_table(self, con) -> None:
        created = apply_as_of_macros(con, "gcalendar")
        assert created == ["gcalendar.calendars_as_of"]

    def test_macro_returns_correct_version_for_timestamp(self, con) -> None:
        apply_as_of_macros(con, "gcalendar")

        # Before the rename: should see "Work"
        rows = con.execute("SELECT id, summary FROM gcalendar.calendars_as_of(TIMESTAMP '2026-01-15 00:00:00')").fetchall()
        assert rows == [("c1", "Work")]

        # After the rename: should see "Day Job"
        rows = con.execute("SELECT id, summary FROM gcalendar.calendars_as_of(TIMESTAMP '2026-03-15 00:00:00')").fetchall()
        assert rows == [("c1", "Day Job")]

    def test_idempotent(self, con) -> None:
        # Re-running just refreshes the macro definition.
        apply_as_of_macros(con, "gcalendar")
        apply_as_of_macros(con, "gcalendar")
        rows = con.execute("SELECT id, summary FROM gcalendar.calendars_as_of(TIMESTAMP '2026-01-15 00:00:00')").fetchall()
        assert rows == [("c1", "Work")]

    def test_ignores_non_scd2_tables(self, con) -> None:
        apply_as_of_macros(con, "gcalendar")
        # The events table has no _dlt_valid_from / _dlt_valid_to, so no macro
        # should have been created for it.
        with pytest.raises(duckdb.Error):
            con.execute("SELECT * FROM gcalendar.events_as_of(TIMESTAMP '2026-01-15 00:00:00')").fetchall()

    def test_handles_table_with_special_chars(self, tmp_path) -> None:
        c = duckdb.connect(str(tmp_path / "special.duckdb"))
        c.execute("CREATE SCHEMA test_schema")
        c.execute(
            """
            CREATE TABLE test_schema."my-weird table" (
                id VARCHAR,
                _dlt_valid_from TIMESTAMP,
                _dlt_valid_to TIMESTAMP
            )
            """
        )
        c.execute("INSERT INTO test_schema.\"my-weird table\" VALUES ('a', TIMESTAMP '2026-01-01', NULL)")
        created = apply_as_of_macros(c, "test_schema")
        assert created == ["test_schema.my-weird table_as_of"]
        rows = c.execute("SELECT id FROM test_schema.\"my-weird table_as_of\"(TIMESTAMP '2026-06-01')").fetchall()
        assert rows == [("a",)]
        c.close()
