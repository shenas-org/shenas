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
      -> Entity            # concrete; shenas_system.entities in user DB
           -> Human         # abstract Python specialization for type='human'
                -> LocalUser  # concrete; shenas_system.local_users in registry DB

``LocalUser`` stays in the device-wide registry DB for login purposes but
inherits ``Entity``'s column definitions via dataclass inheritance, so
there is a single source of truth for "what an entity has" regardless of
which physical table backs the row.

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
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Self

from app.table import Field, Table

if TYPE_CHECKING:
    import duckdb


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
    is_human: Annotated[bool, Field(db_type="BOOLEAN", description="True for humans", db_default="FALSE")] = False
    is_abstract: Annotated[
        bool, Field(db_type="BOOLEAN", description="True for non-instantiable types", db_default="FALSE")
    ] = False
    added_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When seeded", db_default="current_timestamp"),
    ] = None

    @classmethod
    def concrete_types(cls) -> list[Self]:
        """Return all non-abstract (instantiable) entity types."""
        return cls.all(where="is_abstract = FALSE", order_by="name")

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
    row_id: Annotated[int, Field(db_type="INTEGER", description="PK of the target row")] = 0
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

    This is the concrete class backing ``shenas_system.entities`` in the
    per-user DB. Every entity the user tracks (her dog, her house, her
    vehicle, her partner) lives here regardless of type; the ``type``
    column discriminates.

    The current user's own "me" entity is NOT stored here -- it's the
    ``LocalUser`` row in the registry DB, which inherits from
    :class:`Human` (and transitively from ``Entity``) via Python class
    hierarchy so its column layout matches.
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
    birth_year: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Optional year of birth (humans / animals)"),
    ] = None
    added_at: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="When created", db_default="current_timestamp"),
    ] = None
    updated_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When last updated")] = None
    status_changed_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="When status last changed")] = None

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_human(self) -> bool:
        return self.type == "human"

    def age_in_years(self) -> int | None:
        if not self.birth_year:
            return None
        return datetime.now(UTC).year - int(self.birth_year)

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
        if getattr(type(self), "database", "user") != "system":
            EntityIndex(
                uuid=self.uuid,
                db="user",
                table_name=type(self)._Meta.name,
                row_id=self.id,
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
        if getattr(type(self), "database", "user") != "system":
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
        birth_year: int | None = None,
    ) -> Self:
        """Create a new entity row. ``uuid`` is generated if not supplied."""
        row = cls(
            name=name,
            type=type,
            description=description,
            status=status,
            birth_year=birth_year,
        )
        return row.insert()

    @classmethod
    def find_by_uuid(cls, uuid: str) -> Self | None:
        rows = cls.all(where="uuid = ?", params=[uuid], limit=1)
        return rows[0] if rows else None

    @classmethod
    def list_enabled(cls) -> list[Self]:
        return cls.all(where="status = 'enabled'", order_by="added_at")


class Human(Entity):
    """Python-only abstract specialization for humans.

    Does not own a separate physical table -- rows with ``type = 'human'``
    in ``shenas_system.entities`` instantiate as ``Human``. Subclassed by
    :class:`app.local_users.LocalUser`, which DOES have its own physical
    table in the registry DB but reuses the same column layout via
    dataclass inheritance.
    """

    _abstract: ClassVar[bool] = True

    def is_human(self) -> bool:  # type: ignore[override]
        return True


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
        "is_human": False,
        "is_abstract": True,
        "description": "Root of the entity hierarchy.",
    },
    {
        "name": "physical_entity",
        "display_name": "Physical Entity",
        "parent": "entity",
        "icon": "",
        "is_human": False,
        "is_abstract": True,
        "description": "Something that exists in the physical world.",
    },
    {
        "name": "virtual_entity",
        "display_name": "Virtual Entity",
        "parent": "entity",
        "icon": "",
        "is_human": False,
        "is_abstract": True,
        "description": "Something that exists only as an abstraction.",
    },
    {
        "name": "living_entity",
        "display_name": "Living Entity",
        "parent": "physical_entity",
        "icon": "",
        "is_human": False,
        "is_abstract": True,
        "description": "A living being.",
    },
    # Concrete leaf types
    {
        "name": "human",
        "display_name": "Human",
        "parent": "living_entity",
        "icon": "user",
        "is_human": True,
        "is_abstract": False,
        "description": "A person.",
    },
    {
        "name": "animal",
        "display_name": "Animal",
        "parent": "living_entity",
        "icon": "paw-print",
        "is_human": False,
        "is_abstract": False,
        "description": "A pet or other animal.",
    },
    {
        "name": "residence",
        "display_name": "Residence",
        "parent": "physical_entity",
        "icon": "home",
        "is_human": False,
        "is_abstract": False,
        "description": "A home, apartment, or other place people live.",
    },
    {
        "name": "vehicle",
        "display_name": "Vehicle",
        "parent": "physical_entity",
        "icon": "car",
        "is_human": False,
        "is_abstract": False,
        "description": "A car, bike, or other vehicle.",
    },
    {
        "name": "device",
        "display_name": "Device",
        "parent": "physical_entity",
        "icon": "smartphone",
        "is_human": False,
        "is_abstract": False,
        "description": "A phone, watch, or other device.",
    },
    {
        "name": "city",
        "display_name": "City",
        "parent": "physical_entity",
        "icon": "map-pin",
        "is_human": False,
        "is_abstract": False,
        "description": "A city or metropolitan area.",
    },
    {
        "name": "group",
        "display_name": "Group",
        "parent": "virtual_entity",
        "icon": "",
        "is_human": False,
        "is_abstract": True,
        "description": "A collection of people or entities.",
    },
    {
        "name": "organization",
        "display_name": "Organization",
        "parent": "group",
        "icon": "building",
        "is_human": False,
        "is_abstract": False,
        "description": "A company, gym, or other group.",
    },
    {
        "name": "company",
        "display_name": "Company",
        "parent": "organization",
        "icon": "building-2",
        "is_human": False,
        "is_abstract": False,
        "description": "A commercial business entity.",
    },
    {
        "name": "project",
        "display_name": "Project",
        "parent": "virtual_entity",
        "icon": "folder",
        "is_human": False,
        "is_abstract": True,
        "description": "A planned undertaking or endeavour.",
    },
    {
        "name": "software_project",
        "display_name": "Software Project",
        "parent": "project",
        "icon": "code",
        "is_human": False,
        "is_abstract": False,
        "description": "A software repository or codebase.",
    },
    {
        "name": "country",
        "display_name": "Country",
        "parent": "physical_entity",
        "icon": "flag",
        "is_human": False,
        "is_abstract": False,
        "description": "A sovereign nation or territory.",
    },
]


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


def seed_entity_types(con: duckdb.DuckDBPyConnection) -> None:
    """Upsert the default entity types. Idempotent."""
    for row in DEFAULT_ENTITY_TYPES:
        con.execute(
            "INSERT INTO shenas_system.entity_types "
            "(name, display_name, parent, description, icon, is_human, is_abstract) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (name) DO UPDATE SET "
            "display_name = excluded.display_name, "
            "parent = excluded.parent, "
            "description = excluded.description, "
            "icon = excluded.icon, "
            "is_human = excluded.is_human, "
            "is_abstract = excluded.is_abstract",
            [
                row["name"],
                row["display_name"],
                row.get("parent"),
                row["description"],
                row["icon"],
                row["is_human"],
                row.get("is_abstract", False),
            ],
        )


def seed_relationship_types(con: duckdb.DuckDBPyConnection) -> None:
    """Upsert the default relationship types. Idempotent."""
    for row in DEFAULT_RELATIONSHIP_TYPES:
        con.execute(
            "INSERT INTO shenas_system.entity_relationship_types "
            "(name, display_name, description, inverse_name, is_symmetric) "
            "VALUES (?, ?, '', ?, ?) "
            "ON CONFLICT (name) DO UPDATE SET "
            "display_name = excluded.display_name, "
            "inverse_name = excluded.inverse_name, "
            "is_symmetric = excluded.is_symmetric",
            [row["name"], row["display_name"], row["inverse_name"], row["is_symmetric"]],
        )


def seed_me_entity_index(con: duckdb.DuckDBPyConnection, local_user_id: int, local_user_uuid: str) -> None:
    """Upsert the entity_index row pointing at the current user's LocalUser.

    The LocalUser row lives in the registry DB; its matching entity_index
    row lives in the user DB so edges defined in this user's graph can
    reference the user's own row by UUID.
    """
    con.execute(
        "INSERT INTO shenas_system.entity_index (uuid, db, table_name, row_id) "
        "VALUES (?, 'shenas', 'local_users', ?) "
        "ON CONFLICT (uuid) DO UPDATE SET "
        "db = excluded.db, table_name = excluded.table_name, row_id = excluded.row_id",
        [local_user_uuid, local_user_id],
    )


# ---------------------------------------------------------------------------
# "Current user's entity" helper for GraphQL resolvers
# ---------------------------------------------------------------------------


def current_entity(info: Any = None) -> Any:
    """Return the LocalUser row for the current GraphQL request, or None.

    Resolves ``info.context['user_id']`` against the registry DB's
    ``local_users`` table. Because ``LocalUser`` inherits from
    :class:`Human` (and transitively from :class:`Entity`), the returned
    row has the same Entity-shaped columns as any other entity and can
    be serialized the same way.

    Used by query resolvers that accept an optional entity uuid and want
    to default to "me" when it is not specified.
    """
    from app.database import current_user_id
    from app.local_users import LocalUser

    user_id = info.context.get("user_id") if info is not None else current_user_id.get()
    if user_id is None:
        user_id = current_user_id.get()
    return LocalUser.get_by_id(int(user_id))
