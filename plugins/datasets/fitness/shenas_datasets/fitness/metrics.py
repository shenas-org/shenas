from typing import Annotated

from app.table import Field
from shenas_datasets.core import DailyMetricTable

Date = Annotated[str, Field(db_type="DATE", description="Calendar date", category="time")]
Source = Annotated[str, Field(db_type="VARCHAR", description="Data source identifier (e.g. garmin, oura)")]


class DailyHRV(DailyMetricTable):
    """Heart Rate Variability -- one row per (date, source)."""

    class _Meta:
        name = "daily_hrv"
        display_name = "Daily HRV"
        description = "Per-day heart rate variability summary."
        pk = ("date", "source")

    date: Date
    source: Source
    rmssd: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Root mean square of successive differences between heartbeats",
                unit="ms",
                value_range=(0, 200),
                example_value=42.0,
                category="cardiovascular",
                interpretation="Higher values indicate better autonomic nervous system recovery",
            ),
        ]
        | None
    ) = None
    sdnn: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Standard deviation of NN intervals",
                unit="ms",
                value_range=(0, 250),
                example_value=55.0,
                category="cardiovascular",
                interpretation="Reflects overall heart rate variability; higher is generally better",
            ),
        ]
        | None
    ) = None


class DailySleep(DailyMetricTable):
    """Sleep summary -- one row per (date, source)."""

    class _Meta:
        name = "daily_sleep"
        display_name = "Daily Sleep"
        description = "Per-day sleep summary (duration, score, stage breakdown)."
        pk = ("date", "source")

    date: Date
    source: Source
    total_hours: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Total sleep duration",
                unit="hours",
                value_range=(0, 24),
                example_value=7.5,
                category="sleep",
                interpretation="Adults typically need 7-9 hours; consistently below 6 is associated with health risks",
            ),
        ]
        | None
    ) = None
    score: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Overall sleep quality score",
                value_range=(0, 100),
                example_value=78,
                category="sleep",
                interpretation="Higher scores indicate better sleep quality; above 70 is generally good",
            ),
        ]
        | None
    ) = None
    deep_min: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Time spent in deep (slow-wave) sleep",
                unit="minutes",
                value_range=(0, 300),
                example_value=65,
                category="sleep",
                interpretation="Critical for physical recovery; typically 15-25% of total sleep",
            ),
        ]
        | None
    ) = None
    rem_min: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Time spent in REM sleep",
                unit="minutes",
                value_range=(0, 300),
                example_value=90,
                category="sleep",
                interpretation="Important for memory consolidation and emotional regulation; typically 20-25% of total sleep",
            ),
        ]
        | None
    ) = None
    light_min: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Time spent in light sleep",
                unit="minutes",
                value_range=(0, 600),
                example_value=210,
                category="sleep",
                interpretation="Largest portion of sleep; supports general recovery",
            ),
        ]
        | None
    ) = None
    awake_min: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Time spent awake during the sleep period",
                unit="minutes",
                value_range=(0, 300),
                example_value=25,
                category="sleep",
                interpretation="Some waking is normal; excessive waking may indicate sleep disturbance",
            ),
        ]
        | None
    ) = None


class DailyVitals(DailyMetricTable):
    """Key daily vitals -- one row per (date, source)."""

    class _Meta:
        name = "daily_vitals"
        display_name = "Daily Vitals"
        description = "Per-day vital signs and activity totals (HR, steps, calories, SpO2)."
        pk = ("date", "source")

    date: Date
    source: Source
    resting_hr: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Resting heart rate",
                unit="bpm",
                value_range=(30, 120),
                example_value=62,
                category="cardiovascular",
                interpretation="Lower resting HR generally indicates better cardiovascular fitness; athletes may be 40-60 bpm",
            ),
        ]
        | None
    ) = None
    steps: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Total step count for the day",
                value_range=(0, 100000),
                example_value=8500,
                category="activity",
                interpretation="10,000 steps is a common daily goal; any increase from sedentary baseline is beneficial",
            ),
        ]
        | None
    ) = None
    active_kcal: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Calories burned through active movement (excluding basal metabolic rate)",
                unit="kcal",
                value_range=(0, 5000),
                example_value=450,
                category="activity",
                interpretation="Higher values indicate more physical activity;"
                " varies widely by body size and exercise intensity",
            ),
        ]
        | None
    ) = None
    spo2: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Blood oxygen saturation level",
                unit="percent",
                value_range=(70, 100),
                example_value=97.0,
                category="cardiovascular",
                interpretation="Normal range is 95-100%; values below 90% may indicate respiratory issues",
            ),
        ]
        | None
    ) = None


class DailyBody(DailyMetricTable):
    """Body composition -- one row per (date, source)."""

    class _Meta:
        name = "daily_body"
        display_name = "Daily Body Composition"
        description = "Per-day body weight, BMI, body fat, and muscle mass."
        pk = ("date", "source")

    date: Date
    source: Source
    weight_kg: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Body weight",
                unit="kg",
                value_range=(20, 300),
                example_value=75.0,
                category="body_composition",
                interpretation="Track trends over weeks rather than daily fluctuations; 0.5-1kg daily variation is normal",
            ),
        ]
        | None
    ) = None
    bmi: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Body Mass Index (weight / height squared)",
                value_range=(10, 60),
                example_value=24.5,
                category="body_composition",
                interpretation="18.5-24.9 is considered normal; does not account for muscle mass",
            ),
        ]
        | None
    ) = None
    body_fat_pct: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Body fat percentage",
                unit="percent",
                value_range=(3, 60),
                example_value=18.5,
                category="body_composition",
                interpretation="Healthy ranges vary by age and sex; generally 10-20% for men, 18-28% for women",
            ),
        ]
        | None
    ) = None
    muscle_mass_kg: (
        Annotated[
            float,
            Field(
                db_type="DOUBLE",
                description="Skeletal muscle mass",
                unit="kg",
                value_range=(10, 100),
                example_value=32.0,
                category="body_composition",
                interpretation="Higher muscle mass supports metabolic health; track trends alongside body fat",
            ),
        ]
        | None
    ) = None


ALL_TABLES = [DailyHRV, DailySleep, DailyVitals, DailyBody]
