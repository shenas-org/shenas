from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TableKind = Literal["event", "snapshot", "aggregate", "counter"]
"""Semantic kind of a raw source table.

- ``event``: discrete, immutable occurrence with its own native timestamp.
  Examples: a workout, a transaction, an email, a kudo, a comment, a play,
  a calendar event. PK is the natural id; dlt strategy is merge on id.

- ``snapshot``: current state with no temporal axis -- read as of now and
  overwritten on every sync. Examples: user profile, current categories,
  current zones, current top tracks. dlt strategy is replace.

- ``aggregate``: per-window summary that can be re-emitted with updates as
  more data arrives. PK includes the window key (date/hour). Examples:
  daily HRV, daily sleep, daily vitals, daily journal entries. dlt
  strategy is merge on (window_key, ...).

- ``counter``: monotonically increasing scalar where deltas matter. PK is
  the entity id; the counter field grows over time. Example: a piece of
  Strava gear with cumulative distance. dlt strategy is merge on id; the
  consumer can compute deltas across syncs.
"""


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
    db_default: str | None = None  # SQL DEFAULT expression (e.g. "current_timestamp", "'{}'")
    ui_widget: str | None = None  # "text", "number", "toggle", "password", "select", "textarea"
    options: tuple[str, ...] | None = None  # choices for select widgets
