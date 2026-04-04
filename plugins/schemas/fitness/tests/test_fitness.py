import duckdb
import pytest

from shenas_schemas.fitness import (
    ALL_TABLES,
    DailyBody,
    DailyHRV,
    DailySleep,
    DailyVitals,
    Field,
    FitnessSchema,
    generate_ddl,
    table_metadata,
)


class TestField:
    def test_frozen(self) -> None:
        f = Field(db_type="DOUBLE", description="test")
        with pytest.raises(AttributeError):
            f.db_type = "INTEGER"  # type: ignore[misc]

    def test_defaults(self) -> None:
        f = Field(db_type="VARCHAR", description="a field")
        assert f.unit is None
        assert f.value_range is None
        assert f.example_value is None
        assert f.category is None
        assert f.interpretation is None

    def test_full(self) -> None:
        f = Field(
            db_type="DOUBLE",
            description="HRV",
            unit="ms",
            value_range=(0, 200),
            example_value=42.0,
            category="cardiovascular",
            interpretation="higher is better",
        )
        assert f.unit == "ms"
        assert f.value_range == (0, 200)


class TestMetrics:
    def test_all_tables_count(self) -> None:
        assert len(ALL_TABLES) == 4

    def test_canonical_table_names(self) -> None:
        assert set(FitnessSchema.tables) == {"daily_hrv", "daily_sleep", "daily_vitals", "daily_body"}

    def test_each_table_has_pk(self) -> None:
        for cls in ALL_TABLES:
            assert hasattr(cls, "__table__")
            assert hasattr(cls, "__pk__")
            assert len(cls.__pk__) >= 2

    def test_all_tables_have_date_and_source(self) -> None:
        for cls in ALL_TABLES:
            field_names = [f.name for f in cls.__dataclass_fields__.values()]
            assert "date" in field_names
            assert "source" in field_names

    def test_hrv_fields(self) -> None:
        field_names = [f.name for f in DailyHRV.__dataclass_fields__.values()]
        assert "rmssd" in field_names
        assert "sdnn" in field_names

    def test_sleep_fields(self) -> None:
        field_names = [f.name for f in DailySleep.__dataclass_fields__.values()]
        assert "total_hours" in field_names
        assert "deep_min" in field_names
        assert "rem_min" in field_names

    def test_vitals_fields(self) -> None:
        field_names = [f.name for f in DailyVitals.__dataclass_fields__.values()]
        assert "resting_hr" in field_names
        assert "steps" in field_names
        assert "spo2" in field_names

    def test_body_fields(self) -> None:
        field_names = [f.name for f in DailyBody.__dataclass_fields__.values()]
        assert "weight_kg" in field_names
        assert "bmi" in field_names


class TestDDL:
    def test_generate_ddl_hrv(self) -> None:
        ddl = generate_ddl(DailyHRV)
        assert "CREATE TABLE IF NOT EXISTS metrics.daily_hrv" in ddl
        assert "date DATE NOT NULL" in ddl
        assert "source VARCHAR NOT NULL" in ddl
        assert "rmssd DOUBLE" in ddl
        assert "PRIMARY KEY (date, source)" in ddl

    def test_generate_ddl_all_tables(self) -> None:
        for cls in ALL_TABLES:
            ddl = generate_ddl(cls)
            assert f"metrics.{cls.__table__}" in ddl
            assert "PRIMARY KEY" in ddl

    def test_nullable_fields_have_no_not_null(self) -> None:
        ddl = generate_ddl(DailyHRV)
        lines = ddl.split("\n")
        rmssd_line = next(line for line in lines if "rmssd" in line)
        assert "NOT NULL" not in rmssd_line

    def test_pk_fields_have_not_null(self) -> None:
        ddl = generate_ddl(DailyHRV)
        lines = ddl.split("\n")
        date_line = next(line for line in lines if line.strip().startswith("date "))
        assert "NOT NULL" in date_line

    def test_ensure_schema_creates_tables(self) -> None:
        con = duckdb.connect(":memory:")
        FitnessSchema.ensure(con)
        tables = {
            r[0]
            for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        }
        assert tables == set(FitnessSchema.tables)
        con.close()

    def test_ensure_schema_idempotent(self) -> None:
        con = duckdb.connect(":memory:")
        FitnessSchema.ensure(con)
        FitnessSchema.ensure(con)
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        assert len(tables) == 4
        con.close()


class TestIntrospect:
    def test_schema_metadata_returns_all_tables(self) -> None:
        meta = FitnessSchema.metadata()
        assert len(meta) == 4
        names = {t["table"] for t in meta}
        assert names == set(FitnessSchema.tables)

    def test_table_metadata_structure(self) -> None:
        meta = table_metadata(DailyHRV)
        assert meta["table"] == "daily_hrv"
        assert meta["primary_key"] == ["date", "source"]
        assert isinstance(meta["columns"], list)
        assert len(meta["columns"]) == 4

    def test_column_metadata_has_description(self) -> None:
        meta = table_metadata(DailyHRV)
        rmssd = next(c for c in meta["columns"] if c["name"] == "rmssd")
        assert "description" in rmssd
        assert "db_type" in rmssd
        assert rmssd["db_type"] == "DOUBLE"

    def test_column_metadata_has_unit(self) -> None:
        meta = table_metadata(DailyHRV)
        rmssd = next(c for c in meta["columns"] if c["name"] == "rmssd")
        assert rmssd.get("unit") == "ms"

    def test_column_metadata_has_interpretation(self) -> None:
        meta = table_metadata(DailyHRV)
        rmssd = next(c for c in meta["columns"] if c["name"] == "rmssd")
        assert "interpretation" in rmssd

    def test_nullable_flag(self) -> None:
        meta = table_metadata(DailyHRV)
        date_col = next(c for c in meta["columns"] if c["name"] == "date")
        rmssd_col = next(c for c in meta["columns"] if c["name"] == "rmssd")
        assert date_col["nullable"] is False
        assert rmssd_col["nullable"] is True

    def test_all_metric_fields_have_metadata(self) -> None:
        """Every non-PK field should have at least db_type and description."""
        for table_meta in FitnessSchema.metadata():
            for col in table_meta["columns"]:
                assert "db_type" in col, f"{table_meta['table']}.{col['name']} missing db_type"
                assert "description" in col, f"{table_meta['table']}.{col['name']} missing description"


class TestSchema:
    def test_schema_name(self) -> None:
        assert FitnessSchema.name == "fitness"

    def test_schema_tables(self) -> None:
        assert set(FitnessSchema.tables) == {"daily_hrv", "daily_sleep", "daily_vitals", "daily_body"}
