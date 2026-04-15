"""Place-family entity tables: abstract :class:`Place` + concrete City / Residence / Country.

This module owns everything lat/lng-y about the entity model:

- :class:`Place` is the abstract :class:`app.entity.EntityTable` base that any
  table whose rows represent places extends. It injects the ``latitude`` /
  ``longitude`` columns via ``@dataclass`` + ``kw_only`` fields so subclasses
  can declare their own required fields in any order. ``_validate()`` enforces
  that ``_Meta.entity_type`` descends from the built-in ``place`` type.

- :class:`City`, :class:`Residence`, :class:`Country` are the **concrete**
  user-populated tables in the ``entities`` DuckDB schema
  (``entities.cities``, ``entities.residences``, ``entities.countries``).
  Each row carries a deterministic ``entity_id`` (UUIDv5 from entity-type
  name + natural PK) so openmeteo / openaq can fan out over them.

Source plugins that contribute place entities (e.g. a hypothetical Google
Takeout plugin extracting saved locations) just extend :class:`Place` with
the appropriate ``_Meta.entity_type`` -- no need for a per-subtype abstract
intermediate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, ClassVar, Self

from app.entity import (
    EntityTable,
    EntityType,
    _default_entity_types_by_name,
    compute_entity_id,
)
from app.table import Field


def _is_builtin_subtype_of(child_name: str, ancestor_name: str) -> bool:
    """Import-time check: is ``child_name`` a descendant of ``ancestor_name``
    in the built-in :data:`app.entity.DEFAULT_ENTITY_TYPES` hierarchy?

    Like :meth:`EntityType.is_subtype_of` but reads the in-memory defaults
    dict instead of ``cls.all()``, so it's safe to call from ``_validate()``
    at class-definition time (before the DB exists).
    """
    if child_name == ancestor_name:
        return True
    types_by_name = _default_entity_types_by_name()
    current: str | None = child_name
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        entry = types_by_name.get(current)
        if entry is None:
            return False
        if entry.parent == ancestor_name:
            return True
        current = entry.parent
    return False


# ---------------------------------------------------------------------------
# Place: abstract base for all place entity tables
# ---------------------------------------------------------------------------


@dataclass
class Place(EntityTable):
    """An :class:`EntityTable` whose rows represent places on earth.

    Concrete subclasses inherit ``latitude`` and ``longitude`` (decimal
    degrees). ``_Meta.entity_type`` must resolve to ``place`` or a descendant
    (``city`` / ``residence`` / ``country`` / ...) in the built-in entity-type
    hierarchy; this is enforced at class-definition time so plugin authors
    get a loud error if they miscategorize a table.

    The ``@dataclass`` decorator is applied so ``latitude`` / ``longitude``
    are dataclass-inheritable via the normal MRO walk. They are ``kw_only``
    so concrete subclasses can declare their own required (non-default)
    fields without hitting the "defaults before required fields" ordering
    rule.
    """

    _abstract: ClassVar[bool] = True

    latitude: Annotated[
        float,
        Field(db_type="DOUBLE", description="Latitude in decimal degrees", display_name="Latitude"),
    ] = field(default=0.0, kw_only=True)
    longitude: Annotated[
        float,
        Field(db_type="DOUBLE", description="Longitude in decimal degrees", display_name="Longitude"),
    ] = field(default=0.0, kw_only=True)

    @classmethod
    def _validate(cls) -> None:
        super()._validate()
        et_name = cls._Meta.entity_type.name  # type: ignore[attr-defined]
        if not _is_builtin_subtype_of(et_name, "place"):
            msg = (
                f"{cls.__name__}: Place requires `_Meta.entity_type` to descend from 'place'; "
                f"got {et_name!r}. Pick a place subtype via EntityType.default(...) "
                "(city / residence / country / ...) or declare a custom one."
            )
            raise TypeError(msg)


# ---------------------------------------------------------------------------
# Built-in concrete place tables (in the `entities` schema)
# ---------------------------------------------------------------------------
#
# Each non-abstract place subtype gets its own DuckDB table so users can
# populate their places (home city, visited cities, residences, countries) and
# have them automatically picked up by place-consuming sources (openmeteo,
# openaq, any future geo-aware plugin).
#
# Natural PK is ``entity_id`` (UUIDv5 derived from the entity-type name + the
# row's ``name``). Duplicate names collapse onto one entity_id -- users can
# qualify ambiguous names (e.g. "London UK" vs "London ON") or wait for a
# future PR that widens the PK.


@dataclass
class City(Place):
    """User-tracked cities with coordinates.

    Populated manually by the user (via GraphQL mutation or direct insert);
    each row carries a deterministic ``entity_id`` (UUIDv5 derived from the
    entity-type name + ``name``) so openmeteo / openaq can fan out over it.

    Unlike source-contributed :class:`EntityTable` rows, these don't live
    under the SCD2 dlt pipeline -- they're plain user-managed rows.
    ``entity_id`` is an explicit dataclass field (populated via
    :meth:`create`) rather than relying on dlt's schema injection.
    """

    class _Meta:
        name = "cities"
        display_name = "Cities"
        description = "User-tracked cities with coordinates."
        schema = "entities"
        pk = ("entity_id",)
        entity_type = EntityType.default("city")

    entity_id: Annotated[
        str,
        Field(db_type="VARCHAR", description="Stable entity UUID (UUIDv5).", display_name="Entity ID"),
    ] = ""
    name: Annotated[
        str,
        Field(db_type="VARCHAR", description="City name", display_name="Name"),
    ] = ""

    @classmethod
    def create(cls, *, name: str, latitude: float, longitude: float) -> Self:
        """Insert a new city row with auto-computed ``entity_id``."""
        entity_id = compute_entity_id(cls._Meta.entity_type.name, (name,))
        return cls(entity_id=entity_id, name=name, latitude=latitude, longitude=longitude).insert()


@dataclass
class Residence(Place):
    """User-tracked residences (homes, apartments) with coordinates + optional radius."""

    class _Meta:
        name = "residences"
        display_name = "Residences"
        description = "User-tracked residences with coordinates."
        schema = "entities"
        pk = ("entity_id",)
        entity_type = EntityType.default("residence")

    entity_id: Annotated[
        str,
        Field(db_type="VARCHAR", description="Stable entity UUID (UUIDv5).", display_name="Entity ID"),
    ] = ""
    name: Annotated[
        str,
        Field(db_type="VARCHAR", description="Residence name", display_name="Name"),
    ] = ""
    radius_m: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Search radius in meters (e.g. for openaq).", display_name="Radius (m)"),
    ] = None

    @classmethod
    def create(
        cls,
        *,
        name: str,
        latitude: float,
        longitude: float,
        radius_m: int | None = None,
    ) -> Self:
        """Insert a new residence row with auto-computed ``entity_id``."""
        entity_id = compute_entity_id(cls._Meta.entity_type.name, (name,))
        return cls(
            entity_id=entity_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
        ).insert()


@dataclass
class Country(Place):
    """User-tracked countries with coordinates (typically the capital's lat/lng).

    Wikidata columns (``wikidata_qid`` + enrichment fields) are populated by
    the ``wikidata`` source plugin, which upserts into this table via the
    natural name key. They default to ``None`` so manual ``create()`` calls
    still work for offline / custom countries.
    """

    class _Meta:
        name = "countries"
        display_name = "Countries"
        description = "User-tracked countries, optionally enriched from Wikidata."
        schema = "entities"
        pk = ("entity_id",)
        entity_type = EntityType.default("country")

    entity_id: Annotated[
        str,
        Field(db_type="VARCHAR", description="Stable entity UUID (UUIDv5).", display_name="Entity ID"),
    ] = ""
    name: Annotated[
        str,
        Field(db_type="VARCHAR", description="Country name", display_name="Name"),
    ] = ""
    wikidata_qid: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Wikidata Q-ID (e.g. Q183 for Germany)", display_name="Wikidata QID"),
    ] = None
    description: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Short Wikidata description", display_name="Description"),
    ] = None
    iso_alpha_2: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="ISO 3166-1 alpha-2 code (P297)", display_name="ISO2"),
    ] = None
    iso_alpha_3: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="ISO 3166-1 alpha-3 code (P298)", display_name="ISO3"),
    ] = None
    capital_qid: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Capital city Q-ID (P36)", display_name="Capital QID"),
    ] = None
    capital_name: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Capital city name", display_name="Capital"),
    ] = None
    population: Annotated[
        int | None,
        Field(db_type="BIGINT", description="Population (P1082)", display_name="Population"),
    ] = None
    area_km2: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Area in square kilometres (P2046)", display_name="Area", unit="km2"),
    ] = None
    currency_qid: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Currency Q-ID (P38)", display_name="Currency QID"),
    ] = None
    currency_name: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Currency name", display_name="Currency"),
    ] = None
    official_languages: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="Pipe-separated list of official language names (P37)",
            display_name="Official Languages",
        ),
    ] = None

    @classmethod
    def create(cls, *, name: str, latitude: float, longitude: float) -> Self:
        """Insert a new country row with auto-computed ``entity_id``."""
        entity_id = compute_entity_id(cls._Meta.entity_type.name, (name,))
        return cls(entity_id=entity_id, name=name, latitude=latitude, longitude=longitude).insert()


__all__ = [
    "City",
    "Country",
    "Place",
    "Residence",
]
