from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    """Structured metadata for schema fields and config fields.

    Used by canonical metric tables and pipe/component config tables alike.
    The frontend can introspect these to generate UIs on the fly.
    """

    db_type: str
    description: str
    unit: str | None = None
    value_range: tuple[float, float] | None = None
    example_value: float | str | None = None
    category: str | None = None  # "secret", "connection", "schedule", "wellbeing", etc.
    interpretation: str | None = None
    default: str | None = None  # default value (for config fields)
    ui_widget: str | None = None  # "text", "number", "toggle", "password", "select", "textarea"
    options: tuple[str, ...] | None = None  # choices for select widgets
