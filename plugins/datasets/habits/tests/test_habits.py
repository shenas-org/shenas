import duckdb

from shenas_datasets.habits import (
    ALL_TABLES,
    DailyHabits,
    HabitsSchema,
)


class TestMetrics:
    def test_all_tables_count(self) -> None:
        assert len(ALL_TABLES) == 1

    def test_canonical_table_names(self) -> None:
        assert HabitsSchema.tables == ["daily_habits"]

    def test_daily_habits_fields(self) -> None:
        field_names = [f.name for f in DailyHabits.__dataclass_fields__.values()]
        assert "duolingo" in field_names


class TestDDL:
    def test_generate_ddl(self) -> None:
        ddl = DailyHabits.to_ddl()
        assert "CREATE TABLE IF NOT EXISTS metrics.daily_habits" in ddl
        assert "duolingo BOOLEAN" in ddl
        assert "PRIMARY KEY (date, source)" in ddl

    def test_ensure_schema(self) -> None:
        con = duckdb.connect(":memory:")
        HabitsSchema.ensure(con)
        tables = {
            r[0]
            for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        }
        assert "daily_habits" in tables
        con.close()


class TestIntrospect:
    def test_schema_metadata(self) -> None:
        meta = HabitsSchema.metadata()
        assert len(meta) == 1
        assert meta[0]["table"] == "daily_habits"

    def test_column_metadata(self) -> None:
        meta = DailyHabits.table_metadata()
        duo = next(c for c in meta["columns"] if c["name"] == "duolingo")
        assert duo["db_type"] == "BOOLEAN"


class TestSchema:
    def test_schema_name(self) -> None:
        assert HabitsSchema.name == "habits"

    def test_schema_tables(self) -> None:
        assert HabitsSchema.tables == ["daily_habits"]
