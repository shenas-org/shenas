"""Entity tables: digital twins for the user and the things she tracks.

An Entity is a typed node representing something the user cares about --
herself, her dog, her house, her car. Entities are linked via
EntityRelationship edges, and every raw source sync (Garmin activities,
Lunch Money transactions, ...) can be attributed to a specific entity so
one user's DB can hold data about herself and data about her dog
side by side.

Python class hierarchy
----------------------
::

    Table (slim base)
      -> Entity            # concrete; catch-all shenas_system.entities
      -> EntityTable       # abstract; source-side SCD2 entity contributors
           -> PlaceEntityTable
                -> CityEntityTable      -> City       # entities.cities
                -> ResidenceEntityTable -> Residence  # entities.residences
                -> CountryEntityTable   -> Country    # entities.countries

``LocalUser`` lives in its own ``shenas_system.local_users`` table (registry
DB) and doesn't share the ``Entity`` column layout -- it has its own
login-specific columns.

Edges across the Entity / LocalUser split
-----------------------------------------
Because ``Entity`` rows live in the user DB and the current user's
``LocalUser`` row lives in the registry DB, edges can't use a plain
foreign key. Instead, every entity (including the LocalUser) is
registered in :class:`EntityIndex`, a per-user-DB lookup that maps
``uuid -> (db, table, row_id)``. Relationships reference endpoints by
``uuid`` and the index resolves them to physical rows at read time.
"""

from __future__ import annotations

import uuid as uuid_mod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, Self

from app.table import Field, Table

if TYPE_CHECKING:
    from collections.abc import Iterable


# ---------------------------------------------------------------------------
# Sequences and helpers
# ---------------------------------------------------------------------------


ENTITY_SEQ = "shenas_system.entity_seq"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_uuid() -> str:
    """Return a 32-char lowercase hex UUID string (no dashes)."""
    return uuid_mod.uuid4().hex


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------


@dataclass
class EntityType(Table):
    """Lookup of entity kinds (human, animal, residence, vehicle, ...)."""

    class _Meta:
        name = "entity_types"
        display_name = "Entity Types"
        description = "Discriminator values for the entities table."
        schema = "shenas_system"
        pk = ("name",)

    name: Annotated[str, Field(db_type="VARCHAR", description="Short slug, e.g. 'human'")] = ""
    display_name: Annotated[str, Field(db_type="VARCHAR", description="Human-readable label")] = ""
    parent: Annotated[str | None, Field(db_type="VARCHAR", description="Parent type name (hierarchy)")] = None
    description: Annotated[str, Field(db_type="VARCHAR", description="Free-text description", db_default="''")] = ""
    icon: Annotated[str, Field(db_type="VARCHAR", description="Icon hint for the UI", db_default="''")] = ""
    is_abstract: Annotated[
        bool, Field(db_type="BOOLEAN", description="True for non-instantiable types", db_default="FALSE")
    ] = False
    wikidata_qid: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="Wikidata Q-ID for this type class (e.g. 'Q5' for human), or NULL when there is no clean equivalent.",
        ),
    ] = None
    added_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When seeded", db_default="current_timestamp"),
    ] = None

    @classmethod
    def concrete_types(cls) -> list[Self]:
        """Return all non-abstract (instantiable) entity types."""
        return cls.all(where="is_abstract = FALSE", order_by="name")

    @classmethod
    def default(cls, name: str) -> Self:
        """Return the built-in EntityType with ``name`` from DEFAULT_ENTITY_TYPES.

        Pure import-time lookup (no DB access), so it's safe to use at class
        definition for ``EntityTable._Meta.entity_type = EntityType.default("human")``.
        Raises ``KeyError`` on unknown names.
        """
        return _default_entity_types_by_name()[name]  # ty: ignore[invalid-return-type]

    @classmethod
    def is_subtype_of(cls, child: str, ancestor: str) -> bool:
        """Check if ``child`` is a descendant of ``ancestor`` in the type hierarchy."""
        if child == ancestor:
            return True
        all_types = {t.name: t.parent for t in cls.all()}
        current = child
        while current:
            parent = all_types.get(current)
            if parent == ancestor:
                return True
            current = parent
        return False

    def ensure_wide_view(self) -> None:
        """(Re)create ``shenas_system.<self.name>s_wide`` as a dynamic View subclass.

        Discovers every property declared for this type via
        :class:`Property.all`, builds a :class:`~app.view.View` subclass
        with one typed field per property, and calls ``ensure()`` to create
        the DuckDB VIEW. The generated class is cached in
        :data:`_wide_view_registry` so callers can later do
        ``get_wide_view("human").all()``.
        """
        view_cls = _build_wide_view(self.name)
        view_cls.ensure()  # ty: ignore[unresolved-attribute]


# ---------------------------------------------------------------------------
# Dynamic wide-view classes (one per EntityType)
# ---------------------------------------------------------------------------

_wide_view_registry: dict[str, type] = {}


def get_wide_view(type_name: str) -> type:
    """Return the dynamic View subclass for ``<type_name>s_wide``.

    Raises ``KeyError`` if :meth:`EntityType.ensure_wide_view` hasn't
    been called for this type yet (i.e. before bootstrap / first sync).

    Usage::

        HumansWide = get_wide_view("human")
        rows = HumansWide.all(where="date_of_birth IS NOT NULL")
        for r in rows:
            print(r.entity_id, r.name)
    """
    if type_name not in _wide_view_registry:
        msg = f"No wide view for type {type_name!r}. Call ensure_wide_view first."
        raise KeyError(msg)
    return _wide_view_registry[type_name]


def _build_wide_view(type_name: str) -> type:
    """Build (or rebuild) a dynamic View subclass for ``<type_name>s_wide``.

    Reads declared properties for this type via :class:`Property.all`
    (ORM, no raw connection needed), builds the pivot SQL and column
    list, and delegates to :meth:`View.build` for the dataclass + DDL.
    Caches the result in :data:`_wide_view_registry`.
    """
    from app.entities.properties import Property
    from app.view import View

    view_name = type_name + "s_wide"

    # Use all properties declared for this type (seeded at bootstrap,
    # extended by plugins and Wikidata sync). No need to scan statements
    # -- the property registry is the source of truth for column set.
    props = Property.all(
        where="(domain_type IS NULL OR domain_type = ?)",
        params=[type_name],
        order_by="id",
    )

    # The SCD2 _dlt_valid_to column may not exist before the first sync.
    # Use a safe filter: if the view SQL references _dlt_valid_to and the
    # column doesn't exist, DuckDB will error -- so we always include it
    # in the SQL (the VIEW is deferred; the column only needs to exist
    # when the view is queried, not when it's created).
    scd2 = "s._dlt_valid_to IS NULL"

    if props:
        pivots = ",\n  ".join(
            f"MAX(CASE WHEN s.property_id = {_sql_str(p.id)} THEN s.value_label END) AS {_slug(p.label)}" for p in props
        )
    else:
        pivots = "NULL AS _no_properties"

    view_sql = f"""
        SELECT e.uuid AS entity_id,
               e.name,
               {pivots}
        FROM shenas_system.entities e
        LEFT JOIN shenas_system.statements s
          ON s.entity_id = e.uuid AND {scd2}
        WHERE e.type = {_sql_str(type_name)}
        GROUP BY e.uuid, e.name
    """

    columns = [(_slug(p.label), f"Property: {p.label}") for p in props]

    cls = View.build(
        name=view_name,
        display_name=f"{type_name.title()} (wide)",
        sql=view_sql,
        columns=columns,
        pk=("entity_id",),
    )
    _wide_view_registry[type_name] = cls
    return cls


def _sql_str(s: str) -> str:
    """Single-quoted SQL string literal with embedded quotes escaped."""
    return "'" + s.replace("'", "''") + "'"


def _slug(label: str) -> str:
    """Convert a label to a SQL-safe identifier suffix."""
    out = []
    for ch in label.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "/", ".", "_"):
            out.append("_")
    slug = "".join(out).strip("_") or "col"
    if slug[0].isdigit():
        slug = "_" + slug
    return slug


def ensure_all_wide_views() -> None:
    """Recreate the wide view for every concrete EntityType + PlacesWide.

    Called from ``LocalUser._bootstrap_user_db`` and after each sync so
    new properties picked up by projections or Wikidata enrichment become
    visible immediately. No connection argument needed -- uses the ORM
    cursor system internally.
    """
    import logging

    log = logging.getLogger("shenas.entity")
    for et in EntityType.concrete_types():
        try:
            et.ensure_wide_view()
        except Exception:
            log.exception("ensure_wide_view failed for %s", et.name)
    try:
        from app.entities.places import PlacesWide

        PlacesWide.ensure()
    except Exception:
        log.exception("PlacesWide.ensure failed")


@dataclass
class EntityRelationshipType(Table):
    """Lookup of directed relationship kinds (owner_of, lives_in, ...)."""

    class _Meta:
        name = "entity_relationship_types"
        display_name = "Entity Relationship Types"
        description = "Discriminator values for entity_relationships.type."
        schema = "shenas_system"
        pk = ("name",)

    name: Annotated[str, Field(db_type="VARCHAR", description="Short slug, e.g. 'owner_of'")] = ""
    display_name: Annotated[str, Field(db_type="VARCHAR", description="Human-readable label")] = ""
    description: Annotated[str, Field(db_type="VARCHAR", description="Free-text description", db_default="''")] = ""
    inverse_name: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Reverse label (e.g. 'owned by')"),
    ] = None
    is_symmetric: Annotated[
        bool,
        Field(db_type="BOOLEAN", description="True if the relation is symmetric", db_default="FALSE"),
    ] = False
    added_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When seeded", db_default="current_timestamp"),
    ] = None


# ---------------------------------------------------------------------------
# Entity index (UUID -> (db, table, row_id))
# ---------------------------------------------------------------------------


@dataclass
class EntityIndex(Table):
    """UUID-to-row resolver for edges that cross the registry / user DB split.

    Every entity (including the current user's ``LocalUser`` row in the
    registry DB) has a row here in the user DB. Edges reference entities
    by ``uuid``, and the resolver walks this table to find the physical
    row they point at.
    """

    class _Meta:
        name = "entity_index"
        display_name = "Entity Index"
        description = "UUID -> (db, table, row_id) lookup for entity rows."
        schema = "shenas_system"
        pk = ("uuid",)

    uuid: Annotated[str, Field(db_type="VARCHAR", description="Entity UUID (hex, no dashes)")] = ""
    db: Annotated[
        str,
        Field(db_type="VARCHAR", description="Logical DB: 'user' or 'shenas'", db_default="'user'"),
    ] = "user"
    table_name: Annotated[
        str,
        Field(db_type="VARCHAR", description="Physical table holding the row", db_default="'entities'"),
    ] = "entities"
    row_id: Annotated[
        int, Field(db_type="INTEGER", description="Integer PK of the target row (used when the target table has an int PK).")
    ] = 0
    row_key: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description=(
                "String key of the target row when the target table has a non-integer or "
                "composite natural PK (e.g. VARCHAR ids, ('name',) SCD2 tables). For "
                "composite PKs, store the PK tuple slash-joined."
            ),
        ),
    ] = None
    status: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description=(
                "'enabled' | 'disabled'. New virtual entities from source syncs default "
                "to 'disabled' (user opts in per entity); user-created entities are "
                "enabled via Entity.create(). Preserved across resyncs."
            ),
            db_default="'disabled'",
        ),
    ] = "disabled"
    added_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When registered", db_default="current_timestamp"),
    ] = None


# ---------------------------------------------------------------------------
# Entity: the concrete base
# ---------------------------------------------------------------------------


@dataclass
class Entity(Table):
    """A typed node in the entity graph.

    This is the concrete catch-all table backing ``shenas_system.entities``
    in the per-user DB. Every entity the user tracks (her dog, her vehicle,
    her partner) lives here regardless of type -- except those with
    dedicated tables (:class:`City`, :class:`Residence`, :class:`Country`
    in the ``entities`` schema), which exist so that openmeteo / openaq
    and other geo-aware sources can pick them up automatically. The
    ``type`` column discriminates within the catch-all table.

    The current user's own "me" entity is NOT stored here -- it's the
    ``LocalUser`` row in the registry DB (a separate table with its own
    login-oriented columns).
    """

    class _Meta:
        name = "entities"
        display_name = "Entities"
        description = "Typed nodes in the user's entity graph."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[
        int,
        Field(
            db_type="INTEGER",
            description="Entity ID",
            db_default=f"nextval('{ENTITY_SEQ}')",
        ),
    ] = 0
    uuid: Annotated[
        str,
        Field(db_type="VARCHAR", description="Stable entity UUID (hex, 32 chars, no dashes)"),
    ] = ""
    type: Annotated[
        str,
        Field(db_type="VARCHAR", description="Entity type (FK -> entity_types.name)", db_default="'human'"),
    ] = "human"
    name: Annotated[str, Field(db_type="VARCHAR", description="Display name", db_default="''")] = ""
    description: Annotated[str, Field(db_type="VARCHAR", description="Free-text description", db_default="''")] = ""
    status: Annotated[
        str,
        Field(db_type="VARCHAR", description="enabled | disabled | retired", db_default="'enabled'"),
    ] = "enabled"
    added_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When created", db_default="current_timestamp"),
    ] = None
    updated_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When last updated")] = None
    status_changed_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When status last changed")] = None

    # ------------------------------------------------------------------
    # Mutators -- wrap Table primitives to maintain the entity_index
    # ------------------------------------------------------------------

    def insert(self) -> Self:
        """Insert the entity row and register it in the entity_index.

        Subclasses whose rows live in the registry DB (``LocalUser``) skip
        the index registration -- the ``entity_index`` table lives in the
        user DB and is seeded per-user by :func:`seed_me_entity_index`
        when the user's DB is first bootstrapped.
        """
        if not self.uuid:
            self.uuid = _new_uuid()
        super().insert()
        if getattr(type(self)._Meta, "database", "user") != "system":
            EntityIndex(
                uuid=self.uuid,
                db="user",
                table_name=type(self)._Meta.name,
                row_id=self.id,
                status="enabled",
            ).upsert()
        return self

    def save(self) -> Self:
        self.updated_at = _now_iso()
        return super().save()

    def delete(self) -> None:
        """Delete the entity row, its index entry, and any relationships touching it.

        Skipped for system-scoped subclasses (``LocalUser``); cleaning up a
        local user is handled through the normal registry flow.
        """
        if getattr(type(self)._Meta, "database", "user") != "system":
            from app.database import cursor

            uuid_val = self.uuid
            with cursor() as cur:
                cur.execute(
                    "DELETE FROM shenas_system.entity_relationships WHERE from_uuid = ? OR to_uuid = ?",
                    [uuid_val, uuid_val],
                )
                cur.execute("DELETE FROM shenas_system.entity_index WHERE uuid = ?", [uuid_val])
        super().delete()

    # ------------------------------------------------------------------
    # Factories / queries
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        name: str,
        type: str = "human",  # noqa: A002
        description: str = "",
        status: str = "enabled",
    ) -> Self:
        """Create a new entity row. ``uuid`` is generated if not supplied."""
        row = cls(
            name=name,
            type=type,
            description=description,
            status=status,
        )
        return row.insert()

    @classmethod
    def find_by_uuid(cls, uuid: str) -> Self | None:
        rows = cls.all(where="uuid = ?", params=[uuid], limit=1)
        return rows[0] if rows else None

    @classmethod
    def list_enabled(cls) -> list[Self]:
        return cls.all(where="status = 'enabled'", order_by="added_at")


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


@dataclass
class EntityRelationship(Table):
    """A directed relationship between two entities.

    Endpoints are referenced by UUID rather than row id so edges can span
    the registry / user DB split: the current user's ``LocalUser`` row
    lives in the registry DB but every entity is registered in
    :class:`EntityIndex` on the user side, so the resolver can look up
    either endpoint by UUID.
    """

    class _Meta:
        name = "entity_relationships"
        display_name = "Entity Relationships"
        description = "Directed edges between entities."
        schema = "shenas_system"
        pk = ("from_uuid", "to_uuid", "type")

    from_uuid: Annotated[str, Field(db_type="VARCHAR", description="Source entity UUID")] = ""
    to_uuid: Annotated[str, Field(db_type="VARCHAR", description="Target entity UUID")] = ""
    type: Annotated[
        str,
        Field(db_type="VARCHAR", description="Relationship type (FK -> entity_relationship_types.name)"),
    ] = ""
    description: Annotated[str, Field(db_type="VARCHAR", description="Free-text note", db_default="''")] = ""
    added_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When created", db_default="current_timestamp"),
    ] = None
    updated_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When last updated")] = None

    @classmethod
    def for_entity(cls, entity_uuid: str) -> list[Self]:
        """Return every relationship where ``entity_uuid`` is either endpoint."""
        return cls.all(
            where="from_uuid = ? OR to_uuid = ?",
            params=[entity_uuid, entity_uuid],
            order_by="added_at",
        )


# ---------------------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------------------


DEFAULT_ENTITY_TYPES: list[dict[str, Any]] = [
    # Abstract hierarchy nodes (not directly instantiable)
    {
        "name": "entity",
        "display_name": "Entity",
        "parent": None,
        "icon": "",
        "is_abstract": True,
        "wikidata_qid": "Q35120",  # entity
        "description": "Root of the entity hierarchy.",
    },
    {
        "name": "physical_entity",
        "display_name": "Physical Entity",
        "parent": "entity",
        "icon": "",
        "is_abstract": True,
        "wikidata_qid": "Q223557",  # physical object
        "description": "Something that exists in the physical world.",
    },
    {
        "name": "virtual_entity",
        "display_name": "Virtual Entity",
        "parent": "entity",
        "icon": "",
        "is_abstract": True,
        "wikidata_qid": "Q7184903",  # abstract object
        "description": "Something that exists only as an abstraction.",
    },
    {
        "name": "living_entity",
        "display_name": "Living Entity",
        "parent": "physical_entity",
        "icon": "",
        "is_abstract": True,
        "wikidata_qid": "Q7239",  # organism
        "description": "A living being.",
    },
    {
        "name": "place",
        "display_name": "Place",
        "parent": "physical_entity",
        "icon": "map",
        "is_abstract": True,
        "wikidata_qid": "Q17334923",  # location
        "description": "A geographic location: a residence, city, country, or other place.",
    },
    # Concrete leaf types
    {
        "name": "human",
        "display_name": "Human",
        "parent": "living_entity",
        "icon": "user",
        "is_abstract": False,
        "wikidata_qid": "Q5",  # human
        "wikidata_properties": [
            {"pid": "P21", "label": "sex or gender"},
            {"pid": "P569", "label": "date of birth"},
            {"pid": "P19", "label": "place of birth"},
            {"pid": "P27", "label": "country of citizenship"},
            {"pid": "P106", "label": "occupation"},
            {"pid": "P1412", "label": "languages spoken"},
        ],
        "description": "A person.",
    },
    {
        "name": "animal",
        "display_name": "Animal",
        "parent": "living_entity",
        "icon": "paw-print",
        "is_abstract": False,
        "wikidata_qid": "Q729",  # animal
        "wikidata_properties": [
            {"pid": "P105", "label": "taxon rank"},
            {"pid": "P225", "label": "taxon name"},
            {"pid": "P171", "label": "parent taxon"},
            {"pid": "P569", "label": "date of birth"},
            {"pid": "P21", "label": "sex or gender"},
        ],
        "description": "A pet or other animal.",
    },
    {
        "name": "residence",
        "display_name": "Residence",
        "parent": "place",
        "icon": "home",
        "is_abstract": False,
        "wikidata_qid": "Q699405",  # residence
        "wikidata_properties": [
            {"pid": "P17", "label": "country"},
            {"pid": "P625", "label": "coordinate location"},
            {"pid": "P669", "label": "street address"},
            {"pid": "P281", "label": "postal code"},
            {"pid": "P2046", "label": "area"},
            {"pid": "P571", "label": "inception"},
        ],
        "description": "A home, apartment, or other place people live.",
    },
    {
        "name": "vehicle",
        "display_name": "Vehicle",
        "parent": "physical_entity",
        "icon": "car",
        "is_abstract": False,
        "wikidata_qid": "Q42889",  # vehicle
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P571", "label": "inception"},
            {"pid": "P516", "label": "powered by"},
        ],
        "description": "A motorized or human-powered means of transport.",
    },
    {
        "name": "car",
        "display_name": "Car",
        "parent": "vehicle",
        "icon": "car",
        "is_abstract": False,
        "wikidata_qid": "Q1420",  # motor car
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P571", "label": "inception"},
            {"pid": "P516", "label": "powered by"},
            {"pid": "P528", "label": "catalog code"},
            {"pid": "P1622", "label": "drive side"},
        ],
        "description": "An automobile.",
    },
    {
        "name": "motorcycle",
        "display_name": "Motorcycle",
        "parent": "vehicle",
        "icon": "bike",
        "is_abstract": False,
        "wikidata_qid": "Q34493",  # motorcycle
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P571", "label": "inception"},
            {"pid": "P516", "label": "powered by"},
            {"pid": "P2048", "label": "engine displacement"},
        ],
        "description": "A two-wheeled motor vehicle.",
    },
    {
        "name": "boat",
        "display_name": "Boat",
        "parent": "vehicle",
        "icon": "ship",
        "is_abstract": False,
        "wikidata_qid": "Q35872",  # boat
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P571", "label": "inception"},
            {"pid": "P516", "label": "powered by"},
            {"pid": "P2043", "label": "length"},
        ],
        "description": "A watercraft.",
    },
    {
        "name": "device",
        "display_name": "Device",
        "parent": "physical_entity",
        "icon": "smartphone",
        "is_abstract": False,
        "wikidata_qid": "Q1183543",  # device
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P306", "label": "operating system"},
            {"pid": "P571", "label": "inception"},
        ],
        "description": "An electronic device.",
    },
    {
        "name": "mobile_phone",
        "display_name": "Mobile Phone",
        "parent": "device",
        "icon": "smartphone",
        "is_abstract": False,
        "wikidata_qid": "Q17517",  # mobile phone
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P306", "label": "operating system"},
            {"pid": "P571", "label": "inception"},
            {"pid": "P8371", "label": "IMEI"},
        ],
        "description": "A smartphone or other mobile phone.",
    },
    {
        "name": "computer",
        "display_name": "Computer",
        "parent": "device",
        "icon": "laptop",
        "is_abstract": False,
        "wikidata_qid": "Q68",  # computer
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P306", "label": "operating system"},
            {"pid": "P571", "label": "inception"},
            {"pid": "P880", "label": "CPU"},
        ],
        "description": "A laptop, desktop, or other personal computer.",
    },
    {
        "name": "tablet",
        "display_name": "Tablet",
        "parent": "device",
        "icon": "tablet",
        "is_abstract": False,
        "wikidata_qid": "Q155972",  # tablet computer
        "wikidata_properties": [
            {"pid": "P176", "label": "manufacturer"},
            {"pid": "P306", "label": "operating system"},
            {"pid": "P571", "label": "inception"},
        ],
        "description": "A tablet computer.",
    },
    {
        "name": "city",
        "display_name": "City",
        "parent": "place",
        "icon": "map-pin",
        "is_abstract": False,
        "wikidata_qid": "Q515",  # city
        "wikidata_properties": [
            {"pid": "P17", "label": "country"},
            {"pid": "P625", "label": "coordinate location"},
            {"pid": "P421", "label": "located in time zone"},
            {"pid": "P1082", "label": "population"},
            {"pid": "P2046", "label": "area"},
            {"pid": "P2044", "label": "elevation above sea level"},
        ],
        "description": "A city or metropolitan area.",
    },
    {
        "name": "group",
        "display_name": "Group",
        "parent": "virtual_entity",
        "icon": "",
        "is_abstract": True,
        "wikidata_qid": "Q874405",  # social group
        "description": "A collection of people or entities.",
    },
    {
        "name": "organization",
        "display_name": "Organization",
        "parent": "group",
        "icon": "building",
        "is_abstract": False,
        "wikidata_qid": "Q43229",  # organization
        "wikidata_properties": [
            {"pid": "P571", "label": "inception"},
            {"pid": "P17", "label": "country"},
            {"pid": "P159", "label": "headquarters location"},
            {"pid": "P112", "label": "founded by"},
            {"pid": "P856", "label": "official website"},
            {"pid": "P1128", "label": "employees"},
        ],
        "description": "A company, gym, or other group.",
    },
    {
        "name": "company",
        "display_name": "Company",
        "parent": "organization",
        "icon": "building-2",
        "is_abstract": False,
        "wikidata_qid": "Q783794",  # company
        "wikidata_properties": [
            {"pid": "P571", "label": "inception"},
            {"pid": "P17", "label": "country"},
            {"pid": "P159", "label": "headquarters location"},
            {"pid": "P112", "label": "founded by"},
            {"pid": "P169", "label": "chief executive officer"},
            {"pid": "P452", "label": "industry"},
            {"pid": "P414", "label": "stock exchange"},
            {"pid": "P1128", "label": "employees"},
        ],
        "description": "A commercial business entity.",
    },
    {
        "name": "project",
        "display_name": "Project",
        "parent": "virtual_entity",
        "icon": "folder",
        "is_abstract": True,
        "wikidata_qid": "Q170584",  # project
        "description": "A planned undertaking or endeavour.",
    },
    {
        "name": "software_project",
        "display_name": "Software Project",
        "parent": "project",
        "icon": "code",
        "is_abstract": False,
        "wikidata_qid": "Q1141526",  # software project
        "wikidata_properties": [
            {"pid": "P277", "label": "programmed in"},
            {"pid": "P275", "label": "license"},
            {"pid": "P1324", "label": "source code repository URL"},
            {"pid": "P856", "label": "official website"},
            {"pid": "P178", "label": "developer"},
            {"pid": "P571", "label": "inception"},
        ],
        "description": "A software repository or codebase.",
    },
    {
        "name": "country",
        "display_name": "Country",
        "parent": "place",
        "icon": "flag",
        "is_abstract": False,
        "wikidata_qid": "Q6256",  # country
        "wikidata_properties": [
            {"pid": "P297", "label": "ISO 3166-1 alpha-2 code"},
            {"pid": "P36", "label": "capital"},
            {"pid": "P37", "label": "official language"},
            {"pid": "P38", "label": "currency"},
            {"pid": "P1082", "label": "population"},
            {"pid": "P2046", "label": "area"},
            {"pid": "P463", "label": "member of"},
        ],
        "description": "A sovereign nation or territory.",
    },
]


def _default_entity_types_by_name() -> dict[str, EntityType]:
    """Return DEFAULT_ENTITY_TYPES as a name-keyed dict of EntityType instances.

    Built once on first call and cached. Used by :meth:`EntityType.default`
    so EntityTable subclasses can reference built-in types at class-definition
    time without DB access.
    """

    global _DEFAULT_ENTITY_TYPES_BY_NAME
    if _DEFAULT_ENTITY_TYPES_BY_NAME is None:
        _DEFAULT_ENTITY_TYPES_BY_NAME = {
            row["name"]: EntityType(
                name=row["name"],
                display_name=row["display_name"],
                parent=row.get("parent"),
                description=row.get("description", ""),
                icon=row.get("icon", ""),
                is_abstract=row.get("is_abstract", False),
                wikidata_qid=row.get("wikidata_qid"),
            )
            for row in DEFAULT_ENTITY_TYPES
        }
    return _DEFAULT_ENTITY_TYPES_BY_NAME


_DEFAULT_ENTITY_TYPES_BY_NAME: dict[str, EntityType] | None = None


DEFAULT_RELATIONSHIP_TYPES: list[dict[str, Any]] = [
    {"name": "owner_of", "display_name": "Owner of", "inverse_name": "owned by", "is_symmetric": False},
    {"name": "parent_of", "display_name": "Parent of", "inverse_name": "child of", "is_symmetric": False},
    {"name": "lives_in", "display_name": "Lives in", "inverse_name": "houses", "is_symmetric": False},
    {"name": "works_at", "display_name": "Works at", "inverse_name": "employs", "is_symmetric": False},
    {"name": "uses", "display_name": "Uses", "inverse_name": "used by", "is_symmetric": False},
    {"name": "paired_with", "display_name": "Paired with", "inverse_name": "paired with", "is_symmetric": True},
    {"name": "sibling_of", "display_name": "Sibling of", "inverse_name": "sibling of", "is_symmetric": True},
    {"name": "friend_of", "display_name": "Friend of", "inverse_name": "friend of", "is_symmetric": True},
    {"name": "located_in", "display_name": "Located in", "inverse_name": "location of", "is_symmetric": False},
]


def seed_entity_types() -> None:
    """Upsert the default entity types. Idempotent."""
    for row in DEFAULT_ENTITY_TYPES:
        EntityType(
            name=row["name"],
            display_name=row["display_name"],
            parent=row.get("parent"),
            description=row.get("description", ""),
            icon=row.get("icon", ""),
            is_abstract=row.get("is_abstract", False),
            wikidata_qid=row.get("wikidata_qid"),
        ).upsert()


def seed_properties() -> None:
    """Seed shenas_system.properties with each default EntityType's Wikidata PIDs.

    Idempotent. The per-type ``domain_type`` lets WikidataSource discover
    which PIDs apply to a type at sync time.
    """
    from app.entities.properties import Property

    for row in DEFAULT_ENTITY_TYPES:
        type_name = row["name"]
        for prop in row.get("wikidata_properties") or []:
            pid = prop.get("pid")
            label = prop.get("label")
            if not pid or not label:
                continue
            Property.from_row((pid, label, "string", type_name, "wikidata", pid, None)).upsert()


def seed_relationship_types() -> None:
    """Upsert the default relationship types. Idempotent."""
    for row in DEFAULT_RELATIONSHIP_TYPES:
        EntityRelationshipType(
            name=row["name"],
            display_name=row["display_name"],
            inverse_name=row["inverse_name"],
            is_symmetric=row["is_symmetric"],
        ).upsert()


def seed_me_entity_index(local_user_id: int, local_user_uuid: str) -> None:
    """Upsert the entity_index row pointing at the current user's LocalUser.

    The LocalUser row lives in the registry DB; its matching entity_index
    row lives in the user DB so edges defined in this user's graph can
    reference the user's own row by UUID.
    """
    EntityIndex(
        uuid=local_user_uuid,
        db="shenas",
        table_name="local_users",
        row_id=local_user_id,
        status="enabled",
    ).upsert()


# ---------------------------------------------------------------------------
# "Current user's entity" helper for GraphQL resolvers
# ---------------------------------------------------------------------------


def current_entity(info: Any = None) -> Any:
    """Return the LocalUser row for the current GraphQL request, or None.

    Resolves ``info.context['user_id']`` against the registry DB's
    ``local_users`` table.

    Used by query resolvers that accept an optional entity uuid and want
    to default to "me" when it is not specified.
    """
    from app.database import current_user_id
    from app.local_users import LocalUser

    user_id = info.context.get("user_id") if info is not None else current_user_id.get()
    if user_id is None:
        user_id = current_user_id.get()
    return LocalUser.get_by_id(int(user_id))


_ENTITY_ID_NAMESPACE = uuid_mod.uuid5(uuid_mod.NAMESPACE_OID, "shenas:entity")


def compute_entity_id(entity_type_name: str, pk_values: Iterable[object]) -> str:
    """Return a stable UUID for an entity of ``entity_type_name`` with ``pk_values``.

    Uses UUIDv5 under a fixed namespace so the output is deterministic and
    independent of the host machine or process. Same inputs -> same UUID,
    across resyncs and across devices syncing through the mesh daemon.
    Returns the 32-char lowercase hex form (no dashes), matching the
    ``entity_index.uuid`` convention.
    """
    key = f"{entity_type_name}:" + "/".join(str(v) for v in pk_values)
    return uuid_mod.uuid5(_ENTITY_ID_NAMESPACE, key).hex
