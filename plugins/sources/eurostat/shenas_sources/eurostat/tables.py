"""Eurostat source tables.

- ``CityPopulation`` -- total population per city per year from Urban Audit.
- ``CityLabourMarket`` -- employment, unemployment, activity rates per city.
- ``CityEconomy`` -- economic and financial indicators per city.
- ``CityLivingConditions`` -- housing, income, poverty indicators per city.
- ``CityEnvironment`` -- environmental indicators per city.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from app.table import Field
from shenas_sources.core.table import SnapshotTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.eurostat.client import EurostatClient


# Indicator code -> (column_name, display_name, description, unit)
POPULATION_INDICATORS: dict[str, tuple[str, str, str, str | None]] = {
    "DE1001V": ("total_population", "Total Population", "Total resident population", None),
}

LABOUR_INDICATORS: dict[str, tuple[str, str, str, str | None]] = {
    "EC1001V": ("unemployment_rate", "Unemployment Rate", "Unemployment rate (ILO definition)", "percent"),
    "EC1002V": ("activity_rate", "Activity Rate", "Economic activity rate", "percent"),
    "EC1003V": ("employment_rate", "Employment Rate", "Employment rate", "percent"),
    "EC2020V": ("youth_unemployment_rate", "Youth Unemployment", "Youth unemployment rate (15-24)", "percent"),
    "EC3040V": ("gdp_per_capita_pps", "GDP per Capita (PPS)", "GDP per capita in purchasing power standards", "PPS"),
}

LIVING_INDICATORS: dict[str, tuple[str, str, str, str | None]] = {
    "SA1022V": ("avg_price_sqm_apartment", "Avg Price/m2", "Average price per sqm for an apartment", "EUR"),
    "SA1025V": ("avg_rent_sqm_month", "Avg Rent/m2/month", "Average monthly rent per sqm", "EUR"),
}

ENVIRONMENT_INDICATORS: dict[str, tuple[str, str, str, str | None]] = {
    "EN2025V": ("pm10_annual_mean", "PM10 Annual Mean", "Annual mean PM10 concentration", "ug/m3"),
    "EN2026V": ("pm25_annual_mean", "PM2.5 Annual Mean", "Annual mean PM2.5 concentration", "ug/m3"),
    "EN2001V": ("no2_annual_mean", "NO2 Annual Mean", "Annual mean NO2 concentration", "ug/m3"),
}


def _pivot_rows(
    raw_rows: list[dict[str, Any]],
    indicator_map: dict[str, tuple[str, str, str, str | None]],
    city_uuid_map: dict[str, str] | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Pivot Eurostat rows from (city, year, indicator) -> value
    to (city, year) -> {city_uuid, city_code, city_name, year, col1: val1, ...}.
    """
    pivoted: dict[tuple[str, str], dict[str, Any]] = {}
    for row in raw_rows:
        geo = row.get("geo_code", "")
        geo_label = row.get("geo_label", geo)
        time_code = row.get("time_code", "")
        indic = row.get("indic_ur_code", "")
        val = row.get("value")

        if indic not in indicator_map:
            continue

        col_name = indicator_map[indic][0]
        key = (geo, time_code)
        if key not in pivoted:
            city_uuid = (city_uuid_map or {}).get(geo, "")
            pivoted[key] = {
                "city_uuid": city_uuid,
                "city_code": geo,
                "city_name": geo_label,
                "year": time_code,
            }
        pivoted[key][col_name] = val
    return pivoted


class CityPopulation(SnapshotTable):
    """Annual city population from Eurostat Urban Audit."""

    class _Meta:
        name = "city_population"
        display_name = "City Population"
        description = "Total resident population per city per year from Eurostat Urban Audit."
        pk = ("city_uuid", "year")

    city_uuid: Annotated[str, Field(db_type="VARCHAR", description="City entity UUID", display_name="City")] = ""
    city_code: Annotated[
        str, Field(db_type="VARCHAR", description="Urban Audit city code (e.g. DE004C)", display_name="City Code")
    ] = ""
    city_name: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City Name")] = ""
    year: Annotated[str, Field(db_type="VARCHAR", description="Reference year", display_name="Year")] = ""
    total_population: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Total resident population", display_name="Population"),
    ] = None

    @classmethod
    def extract(cls, client: EurostatClient, **context: Any) -> Iterator[dict[str, Any]]:
        raw = client.get_population()
        pivoted = _pivot_rows(raw, POPULATION_INDICATORS, context.get("city_uuid_map"))
        yield from pivoted.values()


class CityLabourMarket(SnapshotTable):
    """City labour market indicators from Eurostat Urban Audit."""

    class _Meta:
        name = "city_labour_market"
        display_name = "City Labour Market"
        description = "Employment, unemployment, and activity rates per city."
        pk = ("city_uuid", "year")

    city_uuid: Annotated[str, Field(db_type="VARCHAR", description="City entity UUID", display_name="City")] = ""
    city_code: Annotated[str, Field(db_type="VARCHAR", description="Urban Audit city code", display_name="City Code")] = ""
    city_name: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City Name")] = ""
    year: Annotated[str, Field(db_type="VARCHAR", description="Reference year", display_name="Year")] = ""
    unemployment_rate: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Unemployment rate (ILO)", display_name="Unemployment", unit="percent"),
    ] = None
    activity_rate: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Economic activity rate", display_name="Activity Rate", unit="percent"),
    ] = None
    employment_rate: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Employment rate", display_name="Employment Rate", unit="percent"),
    ] = None
    youth_unemployment_rate: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Youth unemployment rate (15-24)",
            display_name="Youth Unemployment",
            unit="percent",
        ),
    ] = None
    gdp_per_capita_pps: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="GDP per capita in purchasing power standards",
            display_name="GDP/capita (PPS)",
            unit="PPS",
        ),
    ] = None

    @classmethod
    def extract(cls, client: EurostatClient, **_: Any) -> Iterator[dict[str, Any]]:
        raw = client.get_labour_market()
        pivoted = _pivot_rows(raw, LABOUR_INDICATORS)
        yield from pivoted.values()


class CityLivingConditions(SnapshotTable):
    """City living conditions from Eurostat Urban Audit."""

    class _Meta:
        name = "city_living_conditions"
        display_name = "City Living Conditions"
        description = "Housing prices, rents, and living condition indicators per city."
        pk = ("city_uuid", "year")

    city_uuid: Annotated[str, Field(db_type="VARCHAR", description="City entity UUID", display_name="City")] = ""
    city_code: Annotated[str, Field(db_type="VARCHAR", description="Urban Audit city code", display_name="City Code")] = ""
    city_name: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City Name")] = ""
    year: Annotated[str, Field(db_type="VARCHAR", description="Reference year", display_name="Year")] = ""
    avg_price_sqm_apartment: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Average price per sqm for an apartment",
            display_name="Price/m2",
            unit="EUR",
        ),
    ] = None
    avg_rent_sqm_month: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Average monthly rent per sqm",
            display_name="Rent/m2/month",
            unit="EUR",
        ),
    ] = None

    @classmethod
    def extract(cls, client: EurostatClient, **_: Any) -> Iterator[dict[str, Any]]:
        raw = client.get_living_conditions()
        pivoted = _pivot_rows(raw, LIVING_INDICATORS)
        yield from pivoted.values()


class CityEnvironment(SnapshotTable):
    """City environmental indicators from Eurostat Urban Audit."""

    class _Meta:
        name = "city_environment"
        display_name = "City Environment"
        description = "Annual air quality and environmental indicators per city."
        pk = ("city_uuid", "year")

    city_uuid: Annotated[str, Field(db_type="VARCHAR", description="City entity UUID", display_name="City")] = ""
    city_code: Annotated[str, Field(db_type="VARCHAR", description="Urban Audit city code", display_name="City Code")] = ""
    city_name: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City Name")] = ""
    year: Annotated[str, Field(db_type="VARCHAR", description="Reference year", display_name="Year")] = ""
    pm10_annual_mean: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Annual mean PM10 concentration",
            display_name="PM10",
            unit="ug/m3",
        ),
    ] = None
    pm25_annual_mean: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Annual mean PM2.5 concentration",
            display_name="PM2.5",
            unit="ug/m3",
        ),
    ] = None
    no2_annual_mean: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Annual mean NO2 concentration",
            display_name="NO2",
            unit="ug/m3",
        ),
    ] = None

    @classmethod
    def extract(cls, client: EurostatClient, **_: Any) -> Iterator[dict[str, Any]]:
        raw = client.get_environment()
        pivoted = _pivot_rows(raw, ENVIRONMENT_INDICATORS)
        yield from pivoted.values()


TABLES = (CityPopulation, CityLabourMarket, CityLivingConditions, CityEnvironment)
