"""Tests for EntityTable, compute_entity_id, and EntityType.default()."""

from __future__ import annotations

from typing import Annotated, ClassVar

import pytest

from app.entity import (
    CityEntityTable,
    CountryEntityTable,
    EntityTable,
    EntityType,
    PlaceEntityTable,
    ResidenceEntityTable,
    compute_entity_id,
)
from app.table import Field


def test_compute_entity_id_is_deterministic() -> None:
    """Same inputs must produce the same UUID."""
    a = compute_entity_id("repository", (12345,))
    b = compute_entity_id("repository", (12345,))
    assert a == b
    # 32 hex chars (no dashes, lowercase)
    assert len(a) == 32
    assert a.lower() == a


def test_compute_entity_id_distinguishes_types_and_keys() -> None:
    """Different entity-types or PKs give different UUIDs."""
    assert compute_entity_id("repository", (1,)) != compute_entity_id("user", (1,))
    assert compute_entity_id("repository", (1,)) != compute_entity_id("repository", (2,))


def test_compute_entity_id_composite_pk() -> None:
    """Composite PKs produce a single deterministic UUID."""
    a = compute_entity_id("calendar_event", ("cal1", "event42"))
    b = compute_entity_id("calendar_event", ("cal1", "event42"))
    assert a == b
    assert a != compute_entity_id("calendar_event", ("cal1", "event43"))


def test_entity_type_default_returns_instance() -> None:
    """EntityType.default('human') returns a populated EntityType."""
    human = EntityType.default("human")
    assert human.name == "human"
    assert human.display_name == "Human"
    assert human.is_human is True
    assert human.is_abstract is False
    assert human.parent == "living_entity"


def test_entity_type_default_unknown_raises() -> None:
    with pytest.raises(KeyError):
        EntityType.default("not_a_real_type")


def test_entity_type_default_caches() -> None:
    """Successive calls return the same instance."""
    assert EntityType.default("human") is EntityType.default("human")


def test_entity_table_requires_entity_type() -> None:
    """EntityTable subclass without _Meta.entity_type must fail at class-definition time."""
    with pytest.raises(TypeError, match="EntityTable"):

        class _Missing(EntityTable):
            class _Meta:
                name = "missing"
                display_name = "Missing"
                pk = ("id",)

            id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0


def test_entity_table_rejects_non_entity_type() -> None:
    """_Meta.entity_type must be an EntityType instance, not a string or dict."""
    with pytest.raises(TypeError, match="EntityType instance"):

        class _BadType(EntityTable):
            class _Meta:
                name = "bad"
                display_name = "Bad"
                pk = ("id",)
                entity_type: ClassVar[str] = "repository"  # wrong type

            id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0


def test_entity_table_valid_class() -> None:
    """A well-formed EntityTable subclass defines cleanly and exposes its type."""

    class _Repo(EntityTable):
        class _Meta:
            name = "my_repos"
            display_name = "My Repos"
            pk = ("id",)
            schema = "test"
            entity_type = EntityType(name="test_repo", display_name="Test Repo", parent="virtual_entity")

        id: Annotated[int, Field(db_type="BIGINT", description="repo id")] = 0
        name: Annotated[str, Field(db_type="VARCHAR", description="name")] = ""

    assert _Repo._Meta.entity_type.name == "test_repo"
    # entity_id column is in the dlt schema
    cols = _Repo.to_dlt_columns()
    assert "entity_id" in cols
    assert cols["entity_id"]["data_type"] == "text"
    # table kind is still "dimension" (SCD2 via MRO)
    assert _Repo.table_kind() == "dimension"


# ---------------------------------------------------------------------------
# PlaceEntityTable + subtype bases
# ---------------------------------------------------------------------------


def test_place_entity_table_accepts_place_subtype() -> None:
    """A concrete PlaceEntityTable with entity_type='city' validates cleanly."""

    class _Cities(PlaceEntityTable):
        class _Meta:
            name = "my_cities"
            display_name = "My Cities"
            pk = ("name",)
            schema = "test"
            entity_type = EntityType.default("city")

        name: Annotated[str, Field(db_type="VARCHAR", description="city name")] = ""

    assert _Cities._Meta.entity_type.name == "city"
    # lat/lng inherited from PlaceEntityTable are in the DDL
    ddl = _Cities.to_ddl(schema="test")
    assert "latitude" in ddl
    assert "longitude" in ddl


def test_place_entity_table_rejects_non_place_type() -> None:
    """PlaceEntityTable with entity_type='human' fails at class-definition time."""
    with pytest.raises(TypeError, match="descend from 'place'"):

        class _WrongHumanPlace(PlaceEntityTable):
            class _Meta:
                name = "wrong"
                display_name = "Wrong"
                pk = ("id",)
                schema = "test"
                entity_type = EntityType.default("human")

            id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0


def test_city_entity_table_requires_city_subtype() -> None:
    """CityEntityTable rejects 'residence' (still a place, but not a city)."""
    with pytest.raises(TypeError, match="descend from 'city'"):

        class _NotACity(CityEntityTable):
            class _Meta:
                name = "nope"
                display_name = "Nope"
                pk = ("id",)
                schema = "test"
                entity_type = EntityType.default("residence")

            id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0


def test_residence_entity_table_requires_residence_subtype() -> None:
    """ResidenceEntityTable rejects 'city'."""
    with pytest.raises(TypeError, match="descend from 'residence'"):

        class _NotAResidence(ResidenceEntityTable):
            class _Meta:
                name = "nope2"
                display_name = "Nope2"
                pk = ("id",)
                schema = "test"
                entity_type = EntityType.default("city")

            id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0


def test_country_entity_table_requires_country_subtype() -> None:
    """CountryEntityTable rejects 'city'."""
    with pytest.raises(TypeError, match="descend from 'country'"):

        class _NotACountry(CountryEntityTable):
            class _Meta:
                name = "nope3"
                display_name = "Nope3"
                pk = ("id",)
                schema = "test"
                entity_type = EntityType.default("city")

            id: Annotated[int, Field(db_type="INTEGER", description="id")] = 0
