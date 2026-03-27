import duckdb

from shenas_pipes.core.transform import MetricProviderBase


class GarminMetricProvider(MetricProviderBase):
    source = "garmin"

    def transform(self, con: duckdb.DuckDBPyConnection) -> None:
        self._hrv(con)
        self._sleep(con)
        self._vitals(con)
        self._body(con)

    def _hrv(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_hrv",
            """
            INSERT INTO metrics.daily_hrv (date, source, rmssd)
            SELECT
                calendar_date::DATE,
                'garmin',
                hrv_summary__last_night_avg
            FROM garmin.hrv
            WHERE hrv_summary__last_night_avg IS NOT NULL
            """,
        )

    def _sleep(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_sleep",
            """
            INSERT INTO metrics.daily_sleep
                (date, source, total_hours, score, deep_min, rem_min, light_min, awake_min)
            SELECT
                calendar_date::DATE,
                'garmin',
                daily_sleep_dto__sleep_time_seconds / 3600.0,
                daily_sleep_dto__sleep_scores__overall__value,
                daily_sleep_dto__deep_sleep_seconds / 60,
                daily_sleep_dto__rem_sleep_seconds / 60,
                daily_sleep_dto__light_sleep_seconds / 60,
                daily_sleep_dto__awake_sleep_seconds / 60
            FROM garmin.sleep
            WHERE daily_sleep_dto__sleep_time_seconds IS NOT NULL
            """,
        )

    def _vitals(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_vitals",
            """
            INSERT INTO metrics.daily_vitals (date, source, resting_hr, steps, active_kcal)
            SELECT
                calendar_date::DATE,
                'garmin',
                resting_heart_rate,
                total_steps,
                active_kilocalories::INTEGER
            FROM garmin.daily_stats
            """,
        )

    def _body(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_body",
            """
            INSERT INTO metrics.daily_body (date, source, weight_kg)
            SELECT
                calendar_date::DATE,
                'garmin',
                weight / 1000.0
            FROM garmin.body_composition
            WHERE calendar_date IS NOT NULL
              AND weight IS NOT NULL
            """,
        )
