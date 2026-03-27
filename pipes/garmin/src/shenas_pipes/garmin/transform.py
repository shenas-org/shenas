import duckdb


class GarminMetricProvider:
    source = "garmin"

    def transform(self, con: duckdb.DuckDBPyConnection) -> None:
        self._hrv(con)
        self._sleep(con)
        self._vitals(con)
        self._body(con)

    def _hrv(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("DELETE FROM metrics.daily_hrv WHERE source = 'garmin'")
        con.execute("""
            INSERT INTO metrics.daily_hrv (date, source, rmssd)
            SELECT
                calendar_date::DATE,
                'garmin',
                hrv_summary__last_night_avg
            FROM garmin.hrv
            WHERE hrv_summary__last_night_avg IS NOT NULL
        """)

    def _sleep(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("DELETE FROM metrics.daily_sleep WHERE source = 'garmin'")
        con.execute("""
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
        """)

    def _vitals(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("DELETE FROM metrics.daily_vitals WHERE source = 'garmin'")
        con.execute("""
            INSERT INTO metrics.daily_vitals (date, source, resting_hr, steps, active_kcal)
            SELECT
                calendar_date::DATE,
                'garmin',
                resting_heart_rate,
                total_steps,
                active_kilocalories::INTEGER
            FROM garmin.daily_stats
        """)

    def _body(self, con: duckdb.DuckDBPyConnection) -> None:
        # weight from Garmin is in grams — divide by 1000 for kg
        # bmi/body_fat/muscle_mass only present when a smart scale is used
        con.execute("DELETE FROM metrics.daily_body WHERE source = 'garmin'")
        con.execute("""
            INSERT INTO metrics.daily_body (date, source, weight_kg)
            SELECT
                calendar_date::DATE,
                'garmin',
                weight / 1000.0
            FROM garmin.body_composition
            WHERE calendar_date IS NOT NULL
              AND weight IS NOT NULL
        """)
