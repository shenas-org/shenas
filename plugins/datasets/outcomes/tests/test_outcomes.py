import duckdb

from shenas_datasets.outcomes import (
    ALL_TABLES,
    DailyOutcome,
    OutcomesSchema,
)


class TestMetrics:
    def test_all_tables_count(self) -> None:
        assert len(ALL_TABLES) == 1

    def test_canonical_table_names(self) -> None:
        assert OutcomesSchema.tables == ["daily_outcomes"]

    def test_daily_outcome_fields(self) -> None:
        field_names = [f.name for f in DailyOutcome.__dataclass_fields__.values()]
        assert "mood" in field_names
        assert "stress" in field_names
        assert "productivity" in field_names
        assert "exercise" in field_names
        assert "rosacea" in field_names
        assert "left_ankle" in field_names


class TestDDL:
    def test_generate_ddl(self) -> None:
        ddl = DailyOutcome.to_ddl()
        assert "CREATE TABLE IF NOT EXISTS metrics.daily_outcomes" in ddl
        assert "mood INTEGER" in ddl
        assert "PRIMARY KEY (date, source)" in ddl

    def test_ensure_schema(self) -> None:
        con = duckdb.connect(":memory:")
        OutcomesSchema.ensure(con)
        tables = {
            r[0]
            for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        }
        assert "daily_outcomes" in tables
        con.close()


class TestIntrospect:
    def test_schema_metadata(self) -> None:
        meta = OutcomesSchema.metadata()
        assert len(meta) == 1
        assert meta[0]["table"] == "daily_outcomes"

    def test_column_metadata(self) -> None:
        meta = DailyOutcome.table_metadata()
        mood = next(c for c in meta["columns"] if c["name"] == "mood")
        assert mood["db_type"] == "INTEGER"
        assert mood.get("value_range") == (0, 9)
        assert "interpretation" in mood

    def test_all_fields_have_metadata(self) -> None:
        for col in DailyOutcome.table_metadata()["columns"]:
            assert "description" in col, f"{col['name']} missing description"


class TestSchema:
    def test_schema_name(self) -> None:
        assert OutcomesSchema.name == "outcomes"

    def test_schema_tables(self) -> None:
        assert OutcomesSchema.tables == ["daily_outcomes"]
