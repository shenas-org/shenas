from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    """Structured metadata for a canonical schema field."""

    db_type: str
    description: str
    unit: str | None = None
    value_range: tuple[float, float] | None = None
    example_value: float | str | None = None
    category: str | None = None
    interpretation: str | None = None
