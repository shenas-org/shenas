import duckdb

from shenas_pipes.core.transform import MetricProviderBase


class ObsidianMetricProvider(MetricProviderBase):
    source = "obsidian"

    def transform(self, con: duckdb.DuckDBPyConnection) -> None:
        self._daily_outcomes(con)

    def _daily_outcomes(self, con: duckdb.DuckDBPyConnection) -> None:
        self._upsert(
            con,
            "daily_outcomes",
            """
            INSERT INTO metrics.daily_outcomes
                (date, source, mood, stress, productivity, exercise, friends, family,
                 partner, learning, career, rosacea, left_ankle)
            SELECT
                date::DATE,
                'obsidian',
                mood,
                stress,
                COALESCE(productivity, productive),
                CASE WHEN exercise__v_bool IS NOT NULL
                     THEN CASE WHEN exercise__v_bool THEN 1 ELSE 0 END
                     ELSE exercise
                END,
                friends,
                family,
                partner,
                learning,
                career,
                rosacea,
                left_ankle
            FROM obsidian.daily_notes
            WHERE date IS NOT NULL
            """,
        )
