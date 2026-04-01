import duckdb

from shenas_schemas.outcomes import (
    ALL_TABLES,
    CANONICAL_TABLES,
    SCHEMA,
    DailyOutcome,
    ensure_schema,
    generate_ddl,
    schema_metadata,
    table_metadata,
)


class TestMetrics:
    def test_all_tables_count(self) -> None:
        assert len(ALL_TABLES) == 1

    def test_canonical_table_names(self) -> None:
        assert CANONICAL_TABLES == ["daily_outcomes"]

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
        ddl = generate_ddl(DailyOutcome)
        assert "CREATE TABLE IF NOT EXISTS metrics.daily_outcomes" in ddl
        assert "mood INTEGER" in ddl
        assert "PRIMARY KEY (date, source)" in ddl

    def test_ensure_schema(self) -> None:
        con = duckdb.connect(":memory:")
        ensure_schema(con)
        tables = {
            r[0]
            for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        }
        assert "daily_outcomes" in tables
        con.close()


class TestIntrospect:
    def test_schema_metadata(self) -> None:
        meta = schema_metadata()
        assert len(meta) == 1
        assert meta[0]["table"] == "daily_outcomes"

    def test_column_metadata(self) -> None:
        meta = table_metadata(DailyOutcome)
        mood = [c for c in meta["columns"] if c["name"] == "mood"][0]
        assert mood["db_type"] == "INTEGER"
        assert mood.get("value_range") == (0, 9)
        assert "interpretation" in mood

    def test_all_fields_have_metadata(self) -> None:
        for col in table_metadata(DailyOutcome)["columns"]:
            assert "description" in col, f"{col['name']} missing description"


class TestSchema:
    def test_schema_dict(self) -> None:
        assert SCHEMA["name"] == "outcomes"
        assert SCHEMA["tables"] == ["daily_outcomes"]
