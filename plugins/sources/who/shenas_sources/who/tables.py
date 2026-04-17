"""WHO source tables.

- ``Indicators`` -- lookup of the 22 core WHO GHO indicators (code + name).
- ``IndicatorValues`` -- annual values per (country, year) in **wide form**:
  one column per indicator value plus ``_LOW`` / ``_HIGH`` confidence bounds.

The wide table's columns are generated from ``CORE_INDICATORS`` at import
time via ``types.new_class`` so the indicator list is not duplicated: add
an entry to ``CORE_INDICATORS`` in ``client.py`` and the three matching
columns appear automatically.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING, Annotated, Any

from app.table import Field
from shenas_sources.core.table import AggregateTable, DimensionTable
from shenas_sources.who.client import CORE_INDICATORS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.who.client import WHOClient


class Indicators(DimensionTable):
    """Lookup of WHO GHO core indicators."""

    class _Meta:
        name = "indicators"
        display_name = "Indicators"
        description = "Lookup of the 22 core WHO GHO health indicators tracked by this source."
        pk = ("indicator_code",)

    indicator_code: Annotated[
        str, Field(db_type="VARCHAR", description="WHO GHO indicator code", display_name="Indicator Code")
    ] = ""
    indicator_name: Annotated[str, Field(db_type="VARCHAR", description="Indicator description", display_name="Indicator")] = (
        ""
    )

    @classmethod
    def extract(cls, client: WHOClient, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG003
        for code, name in CORE_INDICATORS.items():
            yield {"indicator_code": code, "indicator_name": name}


def _indicator_values_extract(cls: type, client: WHOClient, **_: Any) -> Iterator[dict[str, Any]]:  # noqa: ARG001
    """Fetch every indicator, pivot into one row per (country_code, year)."""
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for code in CORE_INDICATORS:
        for item in client.get_indicator(code):
            country = item["country_code"]
            year = item["year"]
            if not country or year is None:
                continue
            key = (country, int(year))
            row = rows.setdefault(key, {"country_code": country, "year": int(year)})
            row[code] = item.get("value")
            row[f"{code}_LOW"] = item.get("value_low")
            row[f"{code}_HIGH"] = item.get("value_high")
    yield from rows.values()


def _build_indicator_values_class() -> type[AggregateTable]:
    """Build ``IndicatorValues`` with one column per indicator + _LOW / _HIGH."""
    annotations: dict[str, Any] = {
        "country_code": Annotated[
            str, Field(db_type="VARCHAR", description="ISO 3166-1 alpha-3 country code", display_name="Country Code")
        ],
        "year": Annotated[int, Field(db_type="INTEGER", description="Calendar year", display_name="Year")],
    }
    defaults: dict[str, Any] = {"country_code": "", "year": 0}

    for code, name in CORE_INDICATORS.items():
        annotations[code] = Annotated[
            float | None,
            Field(db_type="DOUBLE", description=f"{name} (value)", display_name=f"{name} (Value)"),
        ]
        annotations[f"{code}_LOW"] = Annotated[
            float | None,
            Field(db_type="DOUBLE", description=f"{name} (lower confidence bound)", display_name=f"{name} (Low)"),
        ]
        annotations[f"{code}_HIGH"] = Annotated[
            float | None,
            Field(db_type="DOUBLE", description=f"{name} (upper confidence bound)", display_name=f"{name} (High)"),
        ]
        defaults[code] = None
        defaults[f"{code}_LOW"] = None
        defaults[f"{code}_HIGH"] = None

    class _Meta:
        name = "indicator_values"
        display_name = "Indicator Values"
        description = (
            "Annual WHO GHO health indicator values per country, wide form: "
            "one column per indicator plus _LOW / _HIGH confidence bounds."
        )
        pk = ("country_code", "year")

    def exec_body(ns: dict[str, Any]) -> None:
        ns["__annotations__"] = annotations
        ns["__module__"] = __name__
        ns["__qualname__"] = "IndicatorValues"
        ns["_Meta"] = _Meta
        ns["time_at"] = "year"
        ns["extract"] = classmethod(_indicator_values_extract)
        ns.update(defaults)

    cls = types.new_class("IndicatorValues", (AggregateTable,), exec_body=exec_body)
    assert issubclass(cls, AggregateTable)
    return cls


IndicatorValues = _build_indicator_values_class()


TABLES = (Indicators, IndicatorValues)
