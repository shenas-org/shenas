from __future__ import annotations

import duckdb

from shenas_pipes.core.transform import MetricProviderBase


class StravaMetricProvider(MetricProviderBase):
    source = "strava"

    def transform(self, con: duckdb.DuckDBPyConnection) -> None:
        self._vitals(con)

    def _vitals(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_vitals",
            """
            INSERT INTO metrics.daily_vitals (date, source, active_kcal)
            SELECT
                start_date_local::DATE,
                'strava',
                SUM(calories)::INTEGER
            FROM strava.activities
            WHERE calories > 0
            GROUP BY start_date_local::DATE
            """,
        )
