import duckdb
import pytest

from shenas_pipes.garmin.transform import GarminMetricProvider


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with raw garmin tables and canonical metrics schema."""
    db = duckdb.connect(":memory:")

    # Create raw garmin schema with test data
    db.execute("CREATE SCHEMA garmin")
    db.execute("""
        CREATE TABLE garmin.hrv (
            calendar_date VARCHAR,
            hrv_summary__last_night_avg INTEGER
        )
    """)
    db.execute("INSERT INTO garmin.hrv VALUES ('2026-03-15', 42), ('2026-03-16', NULL)")

    db.execute("""
        CREATE TABLE garmin.sleep (
            calendar_date VARCHAR,
            daily_sleep_dto__sleep_time_seconds INTEGER,
            daily_sleep_dto__sleep_scores__overall__value INTEGER,
            daily_sleep_dto__deep_sleep_seconds INTEGER,
            daily_sleep_dto__rem_sleep_seconds INTEGER,
            daily_sleep_dto__light_sleep_seconds INTEGER,
            daily_sleep_dto__awake_sleep_seconds INTEGER
        )
    """)
    db.execute("INSERT INTO garmin.sleep VALUES ('2026-03-15', 28800, 78, 3600, 5400, 14400, 1200)")

    db.execute("""
        CREATE TABLE garmin.daily_stats (
            calendar_date VARCHAR,
            resting_heart_rate INTEGER,
            total_steps INTEGER,
            active_kilocalories DOUBLE
        )
    """)
    db.execute("INSERT INTO garmin.daily_stats VALUES ('2026-03-15', 62, 8500, 450.5)")

    db.execute("""
        CREATE TABLE garmin.body_composition (
            calendar_date VARCHAR,
            weight DOUBLE
        )
    """)
    db.execute("INSERT INTO garmin.body_composition VALUES ('2026-03-15', 75000.0), (NULL, 70000.0)")

    # Create canonical metrics schema
    db.execute("CREATE SCHEMA metrics")
    db.execute("""
        CREATE TABLE metrics.daily_hrv (
            date DATE NOT NULL, source VARCHAR NOT NULL, rmssd DOUBLE, sdnn DOUBLE,
            PRIMARY KEY (date, source)
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_sleep (
            date DATE NOT NULL, source VARCHAR NOT NULL, total_hours DOUBLE,
            score INTEGER, deep_min INTEGER, rem_min INTEGER, light_min INTEGER, awake_min INTEGER,
            PRIMARY KEY (date, source)
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_vitals (
            date DATE NOT NULL, source VARCHAR NOT NULL, resting_hr INTEGER,
            steps INTEGER, active_kcal INTEGER, spo2 DOUBLE,
            PRIMARY KEY (date, source)
        )
    """)
    db.execute("""
        CREATE TABLE metrics.daily_body (
            date DATE NOT NULL, source VARCHAR NOT NULL, weight_kg DOUBLE,
            bmi DOUBLE, body_fat_pct DOUBLE, muscle_mass_kg DOUBLE,
            PRIMARY KEY (date, source)
        )
    """)

    return db


class TestGarminTransform:
    def test_hrv(self, con: duckdb.DuckDBPyConnection) -> None:
        GarminMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.daily_hrv").fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "garmin"
        assert rows[0][2] == 42

    def test_sleep(self, con: duckdb.DuckDBPyConnection) -> None:
        GarminMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.daily_sleep").fetchall()
        assert len(rows) == 1
        assert rows[0][2] == 28800 / 3600.0  # total_hours
        assert rows[0][3] == 78  # score
        assert rows[0][4] == 60  # deep_min
        assert rows[0][5] == 90  # rem_min

    def test_vitals(self, con: duckdb.DuckDBPyConnection) -> None:
        GarminMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.daily_vitals").fetchall()
        assert len(rows) == 1
        assert rows[0][2] == 62  # resting_hr
        assert rows[0][3] == 8500  # steps
        assert rows[0][4] == 450  # active_kcal (cast to int)

    def test_body_skips_null_date(self, con: duckdb.DuckDBPyConnection) -> None:
        GarminMetricProvider().transform(con)
        rows = con.execute("SELECT * FROM metrics.daily_body").fetchall()
        assert len(rows) == 1
        assert rows[0][2] == 75.0  # weight_kg (75000 / 1000)

    def test_idempotent(self, con: duckdb.DuckDBPyConnection) -> None:
        provider = GarminMetricProvider()
        provider.transform(con)
        provider.transform(con)
        rows = con.execute("SELECT * FROM metrics.daily_hrv").fetchall()
        assert len(rows) == 1

    def test_source_tag(self, con: duckdb.DuckDBPyConnection) -> None:
        assert GarminMetricProvider.source == "garmin"
