from typing import Annotated, ClassVar

from shenas_datasets.core import MetricTable
from shenas_plugins.core.table import Field

Date = Annotated[str, Field(db_type="DATE", description="Calendar date", category="time")]
Source = Annotated[str, Field(db_type="VARCHAR", description="Data source identifier (e.g. obsidian)")]


class DailyOutcome(MetricTable):
    """Daily self-reported outcomes -- one row per (date, source)."""

    table_name: ClassVar[str] = "daily_outcomes"
    table_display_name: ClassVar[str] = "Daily Outcomes"
    table_description: ClassVar[str | None] = "Per-day self-reported wellbeing, social, and health signals."
    table_pk: ClassVar[tuple[str, ...]] = ("date", "source")

    date: Date
    source: Source
    mood: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Overall mood rating for the day",
                value_range=(0, 9),
                example_value=7,
                category="wellbeing",
                interpretation="Higher values indicate better mood; track trends over weeks rather than individual days",
            ),
        ]
        | None
    ) = None
    stress: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Perceived stress level for the day",
                value_range=(0, 9),
                example_value=4,
                category="wellbeing",
                interpretation="Lower values indicate less stress; elevated stress over multiple days may signal burnout",
            ),
        ]
        | None
    ) = None
    productivity: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Self-assessed productivity rating",
                value_range=(0, 9),
                example_value=6,
                category="performance",
                interpretation="Higher values indicate a more productive day; correlate with sleep and exercise for insights",
            ),
        ]
        | None
    ) = None
    exercise: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Exercise performed (1 = yes, 0 = no, or intensity rating)",
                value_range=(0, 9),
                example_value=1,
                category="health",
                interpretation="Regular exercise correlates with improved mood and energy over time",
            ),
        ]
        | None
    ) = None
    friends: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Social interaction with friends (0 = none, higher = more)",
                value_range=(0, 9),
                example_value=3,
                category="social",
                interpretation="Social connection is a key predictor of wellbeing; track alongside mood",
            ),
        ]
        | None
    ) = None
    family: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Time or interaction with family",
                value_range=(0, 9),
                example_value=2,
                category="social",
                interpretation="Family time supports emotional resilience",
            ),
        ]
        | None
    ) = None
    partner: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Quality time or interaction with partner",
                value_range=(0, 9),
                example_value=4,
                category="social",
                interpretation="Relationship quality affects overall life satisfaction",
            ),
        ]
        | None
    ) = None
    learning: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Time spent learning or studying",
                value_range=(0, 9),
                example_value=2,
                category="growth",
                interpretation="Continuous learning supports career growth and cognitive health",
            ),
        ]
        | None
    ) = None
    career: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Career-focused activity or progress",
                value_range=(0, 9),
                example_value=5,
                category="growth",
                interpretation="Track alongside productivity and stress for work-life balance insights",
            ),
        ]
        | None
    ) = None
    rosacea: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Rosacea skin condition severity",
                value_range=(0, 9),
                example_value=2,
                category="health",
                interpretation="Track triggers by correlating with diet, stress, and exercise patterns",
            ),
        ]
        | None
    ) = None
    left_ankle: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Left ankle pain or condition level",
                value_range=(0, 9),
                example_value=1,
                category="health",
                interpretation="Track recovery progress; correlate with exercise type and intensity",
            ),
        ]
        | None
    ) = None
    daily_duolingo_xp: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Duolingo XP earned today",
                unit="xp",
                value_range=(0, 5000),
                example_value=150,
                category="growth",
                interpretation="Daily language learning effort; correlate with streak and session count",
            ),
        ]
        | None
    ) = None


ALL_TABLES = [DailyOutcome]
