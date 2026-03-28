from dataclasses import dataclass
from typing import Annotated, ClassVar

# Annotated type aliases — the string metadata becomes the DuckDB column type
Date = Annotated[str, "DATE"]


@dataclass
class DailyHRV:
    """Heart Rate Variability — one row per (date, source)."""

    __table__: ClassVar[str] = "daily_hrv"
    __pk__: ClassVar[tuple[str, ...]] = ("date", "source")

    date: Date
    source: str
    rmssd: float | None = None  # ms — root mean square of successive differences
    sdnn: float | None = None   # ms — standard deviation of NN intervals


@dataclass
class DailySleep:
    """Sleep summary — one row per (date, source)."""

    __table__: ClassVar[str] = "daily_sleep"
    __pk__: ClassVar[tuple[str, ...]] = ("date", "source")

    date: Date
    source: str
    total_hours: float | None = None
    score: int | None = None  # 0-100 where available
    deep_min: int | None = None
    rem_min: int | None = None
    light_min: int | None = None
    awake_min: int | None = None


@dataclass
class DailyVitals:
    """Key daily vitals — one row per (date, source)."""

    __table__: ClassVar[str] = "daily_vitals"
    __pk__: ClassVar[tuple[str, ...]] = ("date", "source")

    date: Date
    source: str
    resting_hr: int | None = None  # bpm
    steps: int | None = None
    active_kcal: int | None = None
    spo2: float | None = None  # percent


@dataclass
class DailyBody:
    """Body composition — one row per (date, source)."""

    __table__: ClassVar[str] = "daily_body"
    __pk__: ClassVar[tuple[str, ...]] = ("date", "source")

    date: Date
    source: str
    weight_kg: float | None = None
    bmi: float | None = None
    body_fat_pct: float | None = None
    muscle_mass_kg: float | None = None


ALL_TABLES = [DailyHRV, DailySleep, DailyVitals, DailyBody]
