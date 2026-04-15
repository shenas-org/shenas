"""Numbeo source tables.

- ``CityIndices`` -- composite cost-of-living indices per city (snapshot).
- ``QualityOfLife`` -- quality of life sub-indices per city (snapshot).
- ``CityCrime`` -- crime and safety metrics per city (snapshot).
- ``CityPollution`` -- pollution metrics per city (snapshot).
- ``CityHealthcare`` -- healthcare quality metrics per city (snapshot).
- ``CityTraffic`` -- traffic and commute metrics per city (snapshot).
- ``CityProperty`` -- property market data per city (snapshot).
- ``CityPrices`` -- individual price items per city (snapshot).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from app.table import Field
from shenas_sources.core.table import SnapshotTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.numbeo.client import NumbeoClient


class CityIndices(SnapshotTable):
    """Composite cost-of-living indices per city (NYC = 100 baseline)."""

    class _Meta:
        name = "city_indices"
        display_name = "City Indices"
        description = "Composite cost-of-living, rent, groceries, and purchasing power indices."
        pk = ("city",)

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    cost_of_living_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Cost of Living Index (NYC=100)", display_name="CoL Index"),
    ] = None
    rent_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Rent Index (NYC=100)", display_name="Rent Index"),
    ] = None
    cost_of_living_plus_rent_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Cost of Living Plus Rent Index", display_name="CoL+Rent Index"),
    ] = None
    groceries_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Groceries Index (NYC=100)", display_name="Groceries Index"),
    ] = None
    restaurant_price_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Restaurant Price Index (NYC=100)", display_name="Restaurant Index"),
    ] = None
    local_purchasing_power_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Local Purchasing Power Index (NYC=100)", display_name="Purchasing Power"),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_city_indices(city)
            yield {
                "city": data.get("_city", city),
                "cost_of_living_index": data.get("cpi_index"),
                "rent_index": data.get("rent_index"),
                "cost_of_living_plus_rent_index": data.get("cpi_and_rent_index"),
                "groceries_index": data.get("groceries_index"),
                "restaurant_price_index": data.get("restaurant_price_index"),
                "local_purchasing_power_index": data.get("local_purchasing_power_index"),
            }


class QualityOfLife(SnapshotTable):
    """Quality of life sub-indices per city."""

    class _Meta:
        name = "quality_of_life"
        display_name = "Quality of Life"
        description = "Quality of life indices across 8 categories."
        pk = ("city",)

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    quality_of_life_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Overall quality of life index", display_name="QoL Index"),
    ] = None
    purchasing_power_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Purchasing power index", display_name="Purchasing Power"),
    ] = None
    safety_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Safety index", display_name="Safety"),
    ] = None
    healthcare_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Healthcare index", display_name="Healthcare"),
    ] = None
    climate_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Climate index", display_name="Climate"),
    ] = None
    cost_of_living_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Cost of living index", display_name="Cost of Living"),
    ] = None
    property_price_to_income_ratio: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Property price to income ratio", display_name="Price/Income"),
    ] = None
    traffic_commute_time_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Traffic commute time index", display_name="Traffic"),
    ] = None
    pollution_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Pollution index", display_name="Pollution"),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_quality_of_life(city)
            yield {
                "city": data.get("_city", city),
                "quality_of_life_index": data.get("quality_of_life_index"),
                "purchasing_power_index": data.get("purchasing_power_incl_rent_index"),
                "safety_index": data.get("safety_index"),
                "healthcare_index": data.get("health_care_index"),
                "climate_index": data.get("climate_index"),
                "cost_of_living_index": data.get("cpi_index"),
                "property_price_to_income_ratio": data.get("property_price_to_income_ratio"),
                "traffic_commute_time_index": data.get("traffic_time_index"),
                "pollution_index": data.get("pollution_index"),
            }


class CityCrime(SnapshotTable):
    """Crime and safety metrics per city."""

    class _Meta:
        name = "city_crime"
        display_name = "City Crime"
        description = "Crime levels, safety perception, and specific crime type indices."
        pk = ("city",)

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    crime_index: Annotated[
        float | None, Field(db_type="DOUBLE", description="Overall crime index", display_name="Crime Index")
    ] = None
    safety_index: Annotated[
        float | None, Field(db_type="DOUBLE", description="Overall safety index", display_name="Safety Index")
    ] = None
    crime_increasing: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Crime increasing over past 3 years", display_name="Crime Increasing"),
    ] = None
    safe_walking_day: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Safety of walking alone during day", display_name="Safe Day Walk"),
    ] = None
    safe_walking_night: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Safety of walking alone at night", display_name="Safe Night Walk"),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_city_crime(city)
            yield {
                "city": data.get("_city", city),
                "crime_index": data.get("crime_index"),
                "safety_index": data.get("safety_index"),
                "crime_increasing": data.get("crime_increasing"),
                "safe_walking_day": data.get("safe_walking_day"),
                "safe_walking_night": data.get("safe_walking_night"),
            }


class CityPollution(SnapshotTable):
    """Pollution metrics per city."""

    class _Meta:
        name = "city_pollution"
        display_name = "City Pollution"
        description = "Air, water, noise, and light pollution indices."
        pk = ("city",)

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    pollution_index: Annotated[
        float | None, Field(db_type="DOUBLE", description="Overall pollution index", display_name="Pollution Index")
    ] = None
    air_pollution: Annotated[
        float | None, Field(db_type="DOUBLE", description="Air quality/pollution level", display_name="Air Pollution")
    ] = None
    drinking_water_quality: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Drinking water quality and accessibility", display_name="Water Quality"),
    ] = None
    water_pollution: Annotated[
        float | None, Field(db_type="DOUBLE", description="Water pollution level", display_name="Water Pollution")
    ] = None
    garbage_disposal: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Garbage disposal satisfaction", display_name="Garbage Disposal"),
    ] = None
    noise_light_pollution: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Noise and light pollution level", display_name="Noise/Light"),
    ] = None
    green_spaces: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Green and parks quality", display_name="Green Spaces"),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_city_pollution(city)
            yield {
                "city": data.get("_city", city),
                "pollution_index": data.get("pollution_index"),
                "air_pollution": data.get("air_quality"),
                "drinking_water_quality": data.get("drinking_water_quality_accessibility"),
                "water_pollution": data.get("water_pollution"),
                "garbage_disposal": data.get("garbage_disposal_satisfaction"),
                "noise_light_pollution": data.get("noise_and_light_pollution"),
                "green_spaces": data.get("comfortable_to_spend_time"),
            }


class CityHealthcare(SnapshotTable):
    """Healthcare quality metrics per city."""

    class _Meta:
        name = "city_healthcare"
        display_name = "City Healthcare"
        description = "Healthcare quality, responsiveness, and cost indices."
        pk = ("city",)

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    healthcare_index: Annotated[
        float | None, Field(db_type="DOUBLE", description="Overall healthcare index", display_name="Healthcare Index")
    ] = None
    healthcare_exp_index: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Healthcare expenditure index",
            display_name="Healthcare Cost",
        ),
    ] = None
    skilled_staff: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Skill and competency of medical staff", display_name="Skilled Staff"),
    ] = None
    speed: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Speed of completing examinations/reports", display_name="Speed"),
    ] = None
    modern_equipment: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Modern equipment for diagnosis/treatment", display_name="Equipment"),
    ] = None
    cost: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Cost of medical care satisfaction", display_name="Cost Satisfaction"),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_city_healthcare(city)
            yield {
                "city": data.get("_city", city),
                "healthcare_index": data.get("health_care_index"),
                "healthcare_exp_index": data.get("health_care_exp_index"),
                "skilled_staff": data.get("skill_and_competency"),
                "speed": data.get("speed"),
                "modern_equipment": data.get("modern_equipment"),
                "cost": data.get("cost"),
            }


class CityTraffic(SnapshotTable):
    """Traffic and commute metrics per city."""

    class _Meta:
        name = "city_traffic"
        display_name = "City Traffic"
        description = "Average commute time, traffic inefficiency, and CO2 estimates."
        pk = ("city",)

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    traffic_index: Annotated[
        float | None, Field(db_type="DOUBLE", description="Overall traffic index", display_name="Traffic Index")
    ] = None
    time_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Average commute time index", display_name="Commute Time"),
    ] = None
    time_exp_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Time expenditure index", display_name="Time Exp"),
    ] = None
    inefficiency_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Traffic inefficiency index", display_name="Inefficiency"),
    ] = None
    co2_emission_index: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="CO2 emission index estimate", display_name="CO2 Index"),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_city_traffic(city)
            yield {
                "city": data.get("_city", city),
                "traffic_index": data.get("traffic_index"),
                "time_index": data.get("time_index"),
                "time_exp_index": data.get("time_exp_index"),
                "inefficiency_index": data.get("inefficiency_index"),
                "co2_emission_index": data.get("co2_emission_index"),
            }


class CityProperty(SnapshotTable):
    """Property market data per city."""

    class _Meta:
        name = "city_property"
        display_name = "City Property"
        description = "Property prices per sqm (buy and rent), price-to-income ratios."
        pk = ("city",)

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    price_centre_sqm: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Price per sqm to buy apartment in city centre",
            display_name="Buy Centre/m2",
            unit="USD",
        ),
    ] = None
    price_outside_sqm: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Price per sqm to buy apartment outside centre",
            display_name="Buy Outside/m2",
            unit="USD",
        ),
    ] = None
    rent_centre_1br: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Monthly rent for 1BR apartment in city centre",
            display_name="Rent Centre 1BR",
            unit="USD",
        ),
    ] = None
    rent_outside_1br: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Monthly rent for 1BR apartment outside centre",
            display_name="Rent Outside 1BR",
            unit="USD",
        ),
    ] = None
    price_to_income_ratio: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Property price to annual income ratio", display_name="Price/Income"),
    ] = None
    mortgage_as_pct_income: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Monthly mortgage as percentage of income",
            display_name="Mortgage/Income",
            unit="percent",
        ),
    ] = None
    gross_rental_yield_centre: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Gross rental yield in city centre",
            display_name="Yield Centre",
            unit="percent",
        ),
    ] = None
    gross_rental_yield_outside: Annotated[
        float | None,
        Field(
            db_type="DOUBLE",
            description="Gross rental yield outside city centre",
            display_name="Yield Outside",
            unit="percent",
        ),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_city_property(city)
            yield {
                "city": data.get("_city", city),
                "price_centre_sqm": data.get("price_per_sqm_centre"),
                "price_outside_sqm": data.get("price_per_sqm_outside_centre"),
                "rent_centre_1br": data.get("rent_per_month_1br_centre"),
                "rent_outside_1br": data.get("rent_per_month_1br_outside_centre"),
                "price_to_income_ratio": data.get("price_to_income_ratio"),
                "mortgage_as_pct_income": data.get("mortgage_as_percentage_of_income"),
                "gross_rental_yield_centre": data.get("gross_rental_yield_city_centre"),
                "gross_rental_yield_outside": data.get("gross_rental_yield_outside_centre"),
            }


class CityPrices(SnapshotTable):
    """Individual price items per city (~170 items)."""

    class _Meta:
        name = "city_prices"
        display_name = "City Prices"
        description = "Individual price items: meals, groceries, transport, utilities, rent, salaries."
        pk = ("city", "item_id")

    city: Annotated[str, Field(db_type="VARCHAR", description="City name", display_name="City")] = ""
    item_id: Annotated[int, Field(db_type="INTEGER", description="Numbeo item ID", display_name="Item ID")] = 0
    item_name: Annotated[str, Field(db_type="VARCHAR", description="Item description", display_name="Item")] = ""
    average_price: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Average price in local currency", display_name="Avg Price"),
    ] = None
    min_price: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Minimum reported price", display_name="Min Price"),
    ] = None
    max_price: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Maximum reported price", display_name="Max Price"),
    ] = None

    @classmethod
    def extract(cls, client: NumbeoClient, **_: Any) -> Iterator[dict[str, Any]]:
        for city in client.cities:
            data = client.get_city_prices(city)
            city_name = data.get("_city", city)
            for item in data.get("prices", []):
                yield {
                    "city": city_name,
                    "item_id": item.get("item_id", 0),
                    "item_name": item.get("item_name", ""),
                    "average_price": item.get("average_price"),
                    "min_price": item.get("lowest_price"),
                    "max_price": item.get("highest_price"),
                }


TABLES = (
    CityIndices,
    QualityOfLife,
    CityCrime,
    CityPollution,
    CityHealthcare,
    CityTraffic,
    CityProperty,
    CityPrices,
)
