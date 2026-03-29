from __future__ import annotations

import duckdb

from shenas_pipes.core.transform import MetricProviderBase


class DuolingoMetricProvider(MetricProviderBase):
    source = "duolingo"

    def transform(self, con: duckdb.DuckDBPyConnection) -> None:
        self._daily_xp(con)
        self._daily_habits(con)

    def _daily_xp(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_outcomes",
            """
            INSERT INTO metrics.daily_outcomes (date, source, daily_duolingo_xp)
            SELECT
                date::DATE,
                'duolingo',
                xp_gained
            FROM duolingo.daily_xp
            WHERE xp_gained IS NOT NULL
            """,
        )

    def _daily_habits(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_habits",
            """
            INSERT INTO metrics.daily_habits (date, source, duolingo)
            SELECT
                date::DATE,
                'duolingo',
                xp_gained > 0
            FROM duolingo.daily_xp
            """,
        )
