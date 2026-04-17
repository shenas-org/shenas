"""DuckDB schema namespace registry.

Every DuckDB schema used by the app has a corresponding :class:`Schema`
instance that owns its lifecycle (``CREATE SCHEMA IF NOT EXISTS``) and
serves as the single source of truth for the schema name. Tables
reference a ``Schema`` instance in ``_Meta.schema`` instead of a bare
string, which centralizes creation, prevents typos, and gives the
catalog / frontend a discoverable list of namespaces.

Well-known instances are defined at module level and importable directly::

    from app.schema import CACHE, ENTITIES, METRICS

Source-side schemas (``garmin``, ``strava``, ...) are managed by dlt, not
by this registry. They get a ``Schema`` instance lazily via
:meth:`Schema.source` so the naming is consistent but the lifecycle is
dlt's responsibility.

Usage in a Table class::

    from app.schema import CACHE

    class GeocodeCacheEntry(Table):
        class _Meta:
            name = "geocode"
            display_name = "Geocode Cache"
            pk = ("address_hash",)
            schema = CACHE
"""

from __future__ import annotations

from typing import ClassVar


class Schema:
    """A DuckDB schema namespace."""

    _registry: ClassVar[dict[str, Schema]] = {}

    def __init__(
        self,
        name: str,
        *,
        owner: str = "",
        description: str = "",
        sequences: tuple[str, ...] = (),
    ) -> None:
        self.name = name
        self.owner = owner
        self.description = description
        self.sequences = sequences
        Schema._registry[name] = self

    def __repr__(self) -> str:
        return f"Schema({self.name!r})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Schema):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)

    def ensure(self) -> None:
        """``CREATE SCHEMA IF NOT EXISTS`` + any declared sequences."""
        from app.database import cursor

        with cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.name}"')
            for seq in self.sequences:
                cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {self.name}.{seq} START 1")

    def qualified(self, table_name: str) -> str:
        """Return ``schema.table`` for SQL interpolation."""
        return f"{self.name}.{table_name}"

    @classmethod
    def get(cls, name: str) -> Schema:
        """Look up a registered schema by name. Returns an ad-hoc instance
        if the name isn't pre-registered (for source schemas created by dlt)."""
        return cls._registry.get(name) or cls(name)

    @classmethod
    def source(cls, source_name: str) -> Schema:
        """Return (or create) the Schema for a dlt-managed source.

        Source schemas are lazily registered the first time they're
        referenced. dlt owns the actual ``CREATE SCHEMA`` via its pipeline;
        this just provides a consistent ``Schema`` object.
        """
        if source_name in cls._registry:
            return cls._registry[source_name]
        return cls(source_name, owner="source", description=f"Raw data from {source_name}")

    @classmethod
    def all_registered(cls) -> list[Schema]:
        """Every schema that has been registered (app-managed + source)."""
        return list(cls._registry.values())


# -- Well-known app-managed schemas ------------------------------------------

SHENAS = Schema("shenas", owner="core", description="User accounts and sessions", sequences=("local_user_seq",))
PLUGINS = Schema("plugins", owner="core", description="Installed plugin instances")
PREFERENCES = Schema("ui", owner="core", description="Hotkeys, workspace, and user preferences")
TRANSFORMS = Schema(
    "transforms",
    owner="transforms",
    description="Transform instances and state",
    sequences=("transform_seq", "transform_instance_seq"),
)
ANALYSIS = Schema(
    "analysis",
    owner="analysis",
    description="Hypotheses, findings, recipes",
    sequences=("hypothesis_seq", "finding_seq"),
)
CATALOG = Schema("catalog", owner="catalog", description="Data catalog, geofences, categories", sequences=("geofence_seq",))
ENTITIES = Schema(
    "entities",
    owner="entities",
    description="Entity graph, types, relationships, statements",
    sequences=("entity_seq",),
)
METRICS = Schema("metrics", owner="datasets", description="Canonical derived metric tables")
CACHE = Schema("cache", owner="core", description="Shared caches (LLM, geocode, reverse-geocode)")
MESH = Schema("mesh", owner="mesh", description="Device identity, sync log, sync state")
TELEMETRY = Schema("telemetry", owner="telemetry", description="OpenTelemetry spans and logs")
CONFIG = Schema("config", owner="plugins", description="Per-plugin configuration singletons")
AUTH = Schema("auth", owner="plugins", description="Per-source authentication credentials")
SOURCES = Schema("sources", owner="dlt", description="Raw source data loaded by dlt pipelines")
