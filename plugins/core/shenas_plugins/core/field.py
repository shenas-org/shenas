from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TableKind = Literal["event", "interval", "snapshot", "aggregate", "counter", "dimension"]
"""Semantic kind of a raw source table.

The kind drives how the kind-aware loader (Table ABC in
``shenas_sources.core.table``) writes the table into DuckDB so that every
row in every raw table is time-series-queryable.

- ``event``: discrete, immutable occurrence at a single point in time.
  Declares ``time_at`` (the timestamp column). PK is the natural id.
  dlt strategy is merge on id. Examples: a transaction, an email, a
  kudo, a comment, a play. Tables without a native timestamp get an
  ``observed_at`` column auto-injected from the sync time.

- ``interval``: discrete occurrence with both a start and an end
  timestamp. Declares ``time_start`` and ``time_end``. PK is the natural
  id. dlt strategy is merge on id. Examples: a calendar event, a workout
  with start + duration, a sleep session, a location visit.

- ``snapshot``: current self-state with no native temporal axis. Loaded
  as SCD2 (hash-then-version) so every observed change becomes a new row
  with disjoint ``_dlt_valid_from`` / ``_dlt_valid_to`` ranges. Nothing
  else joins to it -- it's leaf state. Examples: the authenticated user
  profile, current top-tracks ranking, athlete stats, vacation
  responder. dlt strategy is merge with strategy=scd2.

- ``dimension``: reference / lookup data that other tables join against.
  Same SCD2 loader as snapshot but flagged separately so dashboards know
  which tables are *joinable lookups*. Historical joins return the value
  that was true at the time, not the current value -- yesterday's
  rename of "Coffee" -> "Coffee & Tea" no longer rewrites every
  historical transaction. Examples: gcalendar.calendars (events join on
  calendar_id), gmail.labels, lunchmoney.categories / tags / assets /
  plaid_accounts, gcalendar.colors.

- ``aggregate``: per-window summary that can be re-emitted with updates
  as more data arrives. PK includes the window key (date/hour) and that
  same key is the ``time_at``. dlt strategy is merge on
  (window_key, ...). Examples: daily HRV, daily sleep, daily vitals,
  daily journal entries.

- ``counter``: monotonically growing scalar where deltas matter. Loaded
  as append-with-``observed_at`` so consumers can compute deltas across
  observations rather than just reading the latest cumulative value.
  Declares ``counter_columns`` to identify which columns are cumulative.
  Example: a piece of Strava gear with cumulative distance.
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
