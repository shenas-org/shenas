"""Source plugin ABC."""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import re
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

from app.plugin import Plugin
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig

logger = Plugin.get_logger(__name__)

# ISO 8601 recurring-interval parser: "R/P1D", "R/PT1H", "R/P2W", "R/PT15M", etc.
# Supports the subset of durations we actually use for sync cadence: weeks,
# days, hours, minutes, seconds. Returns minutes (or None on parse failure /
# empty input). Kept inline to avoid pulling in `isodate`.
_ISO_RECURRING_RE = re.compile(
    r"^R/P(?:(?P<weeks>\d+)W)?"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def _iso8601_recurring_to_minutes(value: str) -> int | None:
    """Parse an ISO 8601 recurring interval like ``R/P1D`` to minutes.

    Returns ``None`` if ``value`` is empty or not a recognized pattern.
    """
    if not value:
        return None
    m = _ISO_RECURRING_RE.match(value)
    if not m:
        return None
    parts = {k: int(v) for k, v in m.groupdict().items() if v}
    if not parts:
        return None
    total = (
        parts.get("weeks", 0) * 7 * 24 * 60
        + parts.get("days", 0) * 24 * 60
        + parts.get("hours", 0) * 60
        + parts.get("minutes", 0)
        + parts.get("seconds", 0) // 60
    )
    return total or None


class Source(Plugin):
    """Data source plugin.

    Subclass this, set class attributes, and implement ``resources()``.
    The base class provides default ``sync()`` (build_client -> resources ->
    run_sync -> auto_transform) and auto-derived auth_fields / table_name.
    """

    _kind = "source"

    Config: ClassVar[type] = SourceConfig
    Auth: ClassVar[type] = SourceAuth

    auth_instructions: ClassVar[str] = ""
    primary_table: ClassVar[str] = ""
    entity_types: ClassVar[list[str]] = []  # references EntityType.name
    # ISO 8601 recurring interval describing the source's natural cadence
    # (e.g. "R/P1D" for daily, "R/P1W" for weekly, "R/PT1H" for hourly).
    # Mirrors DCAT's `dct:accrualPeriodicity`. Used as the fallback when
    # the per-instance `sync_frequency` config row is unset (see
    # :meth:`sync_frequency`). Empty string means no default cadence.
    default_update_frequency: ClassVar[str] = ""

    # Class-level sync lock: prevents concurrent syncs of the same source
    _sync_locks: ClassVar[dict[str, threading.Lock]] = {}
    _sync_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name"):
            return
        # Auto-set _Meta.name on Config/Auth classes (one row per source), then
        # call _finalize() to apply the deferred @dataclass + Table validation.
        config_table_name = f"source_{cls.name}"
        if cls.Config is SourceConfig:
            # Source uses base SourceConfig -- create a per-source subclass so the table name is unique.
            config_meta = type("_Meta", (SourceConfig._Meta,), {"name": config_table_name})
            cls.Config = type(f"{cls.name.title()}Config", (SourceConfig,), {"_Meta": config_meta})
        elif getattr(cls.Config._Meta, "name", None) in (None, ""):  # ty: ignore[unresolved-attribute]
            cls.Config._Meta = type("_Meta", (cls.Config._Meta,), {"name": config_table_name})  # ty: ignore[invalid-assignment, unresolved-attribute]
        cls.Config._finalize()  # ty: ignore[unresolved-attribute]
        if cls.Auth is not SourceAuth:
            if getattr(cls.Auth._Meta, "name", None) in (None, ""):  # ty: ignore[unresolved-attribute]
                cls.Auth._Meta = type("_Meta", (cls.Auth._Meta,), {"name": config_table_name})  # ty: ignore[invalid-assignment, unresolved-attribute]
            cls.Auth._finalize()  # ty: ignore[unresolved-attribute]
        # Auto-set _Meta.schema to SOURCES and prefix _Meta.name with the
        # source name so all source data lives in one schema:
        #   garmin.activities -> sources.garmin__activities
        from app.plugin import Plugin
        from app.schema import SOURCES

        for t in Plugin.load_tables(cls.name, kind="source"):
            overrides: dict[str, object] = {}
            if not getattr(t._Meta, "schema", None) or t._Meta.schema != SOURCES:  # ty: ignore[unresolved-attribute]
                overrides["schema"] = SOURCES
            name = t._Meta.name  # ty: ignore[unresolved-attribute]
            prefixed = f"{cls.name}__{name}"
            if not name.startswith(f"{cls.name}__"):
                overrides["name"] = prefixed
            if overrides:
                t._Meta = type("_Meta", (t._Meta,), overrides)  # ty: ignore[unresolved-attribute]

    # -- Auth field derivation ------------------------------------------------

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        """Derive auth input fields from Auth dataclass metadata.

        Override for custom prompts that differ from stored field names.
        """
        if self.Auth is SourceAuth:
            return []

        columns = self.Auth.column_metadata()  # ty: ignore[unresolved-attribute]
        fields: list[dict[str, str | bool]] = []
        for col in columns:
            if col["name"] == "id":
                continue
            fields.append(
                {
                    "name": col["name"],
                    "prompt": col.get("description") or col["name"].replace("_", " ").title(),
                    "hide": col.get("category") == "secret",
                }
            )
        return fields

    @property
    def has_auth(self) -> bool:
        return self.Auth is not SourceAuth

    @property
    def is_authenticated(self) -> bool | None:
        """Whether stored credentials exist. None if auth not required."""
        if not self.has_auth:
            return True
        try:
            row = self.Auth.read_row()  # ty: ignore[unresolved-attribute]
            return bool(row and any(v for k, v in row.items() if k != "id"))
        except Exception:
            return None

    @property
    def sync_frequency(self) -> int | None:
        """Sync frequency in minutes.

        Order of precedence:

        1. Explicit ``sync_frequency`` on the per-instance Config row.
        2. ``default_update_frequency`` ClassVar parsed from ISO 8601
           (e.g. ``"R/P1D"`` -> 1440 minutes).
        3. ``None`` (no scheduled sync).
        """
        if self.Config is not SourceConfig:
            try:
                row = self.Config.read_row()  # ty: ignore[unresolved-attribute]
                if row and row.get("sync_frequency") is not None:
                    return row["sync_frequency"]
            except Exception:
                pass
        return _iso8601_recurring_to_minutes(self.default_update_frequency)

    @property
    def is_due_for_sync(self) -> bool:
        """Whether this source's sync frequency has elapsed since last sync."""
        freq = self.sync_frequency
        if freq is None:
            return False
        s = self.instance()
        if not s or not s.enabled:
            return False
        synced_at = s.synced_at
        if not synced_at:
            return True
        from datetime import timedelta

        # DuckDB TIMESTAMP columns come back as ``datetime``; legacy rows may
        # still hold an ISO string. Accept both.
        if isinstance(synced_at, datetime):
            last = synced_at
        else:
            try:
                last = datetime.fromisoformat(str(synced_at))
            except (TypeError, ValueError):
                return True
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        return datetime.now(UTC) - last >= timedelta(minutes=freq)

    @property
    def has_data(self) -> bool:
        return True  # Sources sync data into DuckDB

    @property
    def has_config(self) -> bool:
        return True  # All sources have config (at minimum sync_frequency)

    @property
    def commands(self) -> list[str]:
        cmds = ["sync"]
        if self.has_auth:
            cmds.append("auth")
        return cmds

    def get_config_entries(self) -> list[dict[str, str | None]]:
        """Return config entries for UI display (key, label, value, description)."""
        if not self.has_config:
            return []

        row = self.Config.read_row()  # ty: ignore[unresolved-attribute]
        columns = self.Config.column_metadata()  # ty: ignore[unresolved-attribute]
        entries = []
        for col in columns:
            if col["name"] == "id":
                continue
            val = row.get(col["name"]) if row else None
            is_secret = col.get("category") == "secret"
            display_val = "********" if (is_secret and val) else (str(val) if val is not None else None)
            entry: dict[str, str | None] = {
                "key": col["name"],
                "label": col.get("display_name") or col["name"].replace("_", " ").title(),
                "value": display_val,
                "description": col.get("description", ""),
            }
            if col.get("ui_widget"):
                entry["ui_widget"] = col["ui_widget"]
            if col.get("example_value") is not None:
                entry["default_value"] = str(col["example_value"])
            entries.append(entry)
        return entries

    def set_config_value(self, key: str, value: str | None) -> None:
        """Set a config value with type coercion from string."""
        if not self.has_config:
            return
        if value is not None:
            columns = self.Config.column_metadata()  # ty: ignore[unresolved-attribute]
            for col in columns:
                if col["name"] == key:
                    db_type = col.get("db_type", "").upper()
                    if db_type == "INTEGER":
                        value = int(value)  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
                    elif db_type in ("FLOAT", "DOUBLE", "REAL"):
                        value = float(value)  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
                    break
        self.Config.write_row(**{key: value})  # ty: ignore[unresolved-attribute]

    def get_config_value(self, key: str) -> Any | None:
        """Get a single config value."""
        return self.Config.read_value(key) if self.has_config else None  # ty: ignore[unresolved-attribute]

    def delete_config(self) -> None:
        """Delete all config."""
        if self.has_config:
            self.Config.clear_rows()  # ty: ignore[unresolved-attribute]

    def get_info(self) -> dict[str, Any]:
        return {
            **super().get_info(),
            "is_authenticated": self.is_authenticated,
            "sync_frequency": self.sync_frequency,
            "primary_table": self._qualified_primary_table(),
            "entity_types": self.entity_types,
            "entity_uuids": self._source_entity_uuids(),
            "default_update_frequency": self.default_update_frequency,
            "commands": self.commands,
            "table_metadata": self._table_metadata(),
        }

    def _qualified_primary_table(self) -> str:
        """Return the primary_table with source prefix if not already qualified."""
        table = self.primary_table
        if not table or "." in table:
            return table
        return f"{self.name}__{table}"

    def _table_metadata(self) -> list[dict[str, Any]]:
        """Return table metadata from the TABLES tuple, enriched with live stats.

        Each entry gets ``rows``, ``earliest``, and ``latest`` from DuckDB
        when the table exists (0/null otherwise).
        """

        from app.plugin import Plugin

        tables = list(Plugin.load_tables(self.name, kind="source"))
        views = list(Plugin.load_views(self.name))
        result: list[dict[str, Any]] = []
        for relation in [*tables, *views]:
            if not (isinstance(relation, type) and hasattr(relation, "metadata")):
                continue
            try:
                meta = relation.metadata()  # ty: ignore[call-non-callable]
                if hasattr(meta.get("schema"), "name"):
                    meta["schema"] = meta["schema"].name
                meta.update(self._live_table_stats(meta.get("schema", "sources"), meta["table"]))
                result.append(meta)
            except Exception:
                continue
        return result

    @staticmethod
    def _live_table_stats(schema: str, table: str) -> dict[str, Any]:
        """Query DuckDB for row count and date range of a table."""
        try:
            from app.database import cursor

            qualified = f'"{schema}"."{table}"'
            with cursor() as cur:
                row = cur.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()
                rows = row[0] if row else 0
                earliest = None
                latest = None
                for date_col in ("date", "calendar_date", "start_time_local", "occurred_at"):
                    try:
                        result = cur.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {qualified}").fetchone()
                        if result and result[0]:
                            earliest = str(result[0])[:10]
                            latest = str(result[1])[:10]
                            break
                    except Exception:
                        continue
                return {"rows": rows, "earliest": earliest, "latest": latest}
        except Exception:
            return {"rows": 0, "earliest": None, "latest": None}

    def _source_entity_uuids(self) -> list[str]:
        """Return entity UUIDs this source is about.

        Combines two sources:
        1. Entities produced by this source (via ``entities.statements``).
        2. The "me" entity if this source declares ``"human"`` in
           ``entity_types`` (data about the user, even without explicit
           entity projection).
        """
        uuids: list[str] = []
        seen: set[str] = set()
        # "human" in entity_types -> include "me".
        if "human" in self.entity_types:
            me_uuids = self.resolve_entity_uuids(["human"])
            for uuid in me_uuids:
                if uuid not in seen:
                    seen.add(uuid)
                    uuids.append(uuid)
        # Entities this source actually produced (via statements).
        try:
            from app.entities.statements import Statement
            from app.entity import Entity

            source_entity_ids = Statement.distinct_values("entity_id", where="source = ?", params=[self.name])
            for entity_id in source_entity_ids:
                if entity_id in seen:
                    continue
                entity = Entity.find_by_uuid(entity_id)
                if entity and entity.status == "enabled":
                    seen.add(entity_id)
                    uuids.append(entity_id)
        except Exception:
            pass
        return uuids

    # -- Entity type registration ----------------------------------------------

    def register_entity_types(self) -> None:
        """Upsert entity types declared in this source's ``entities.py``.

        Each source plugin may define ``ENTITY_TYPES`` in its
        ``shenas_sources.<name>.entities`` module. On enable (and at
        startup for already-enabled sources), these types are upserted
        into ``entities.entity_types`` together with their Wikidata
        properties.
        """
        import importlib

        try:
            entities_mod = importlib.import_module(f"shenas_sources.{self.name}.entities")
        except ImportError:
            return

        type_rows = getattr(entities_mod, "ENTITY_TYPES", None) or []
        if not type_rows:
            return

        from app.entities.properties import Property
        from app.entity import EntityType

        for row in type_rows:
            EntityType(
                name=row["name"],
                display_name=row["display_name"],
                parent=row.get("parent"),
                description=row.get("description", ""),
                icon=row.get("icon", ""),
                is_abstract=row.get("is_abstract", False),
                wikidata_qid=row.get("wikidata_qid"),
                wikidata_seed=row.get("wikidata_seed", False),
            ).upsert()
            type_name = row["name"]
            for prop in row.get("wikidata_properties") or []:
                pid = prop.get("pid")
                label = prop.get("label")
                if not pid or not label:
                    continue
                Property.from_row((pid, label, "string", type_name, "wikidata", pid, None)).upsert()

        logger.info("Registered %d entity types for %s", len(type_rows), self.name)

    def deregister_entity_types(self) -> None:
        """Remove entity types declared in this source's ``entities.py``."""
        import importlib

        try:
            entities_mod = importlib.import_module(f"shenas_sources.{self.name}.entities")
        except ImportError:
            return

        type_rows = getattr(entities_mod, "ENTITY_TYPES", None) or []
        if not type_rows:
            return

        from app.entity import EntityType

        for row in type_rows:
            existing = EntityType.find(row["name"])
            if existing is not None:
                existing.delete()

        logger.info("Deregistered %d entity types for %s", len(type_rows), self.name)

    # -- Sync lifecycle -------------------------------------------------------

    def _lookback_start_date(self, default_days: int) -> str:
        """Read ``lookback_period`` from Config, fall back to ``default_days``.

        Sources that support a configurable lookback call this from
        ``resources()`` to get the ``start_date`` string. The Config field
        is in days; the return value is ``"N days ago"`` for
        :func:`resolve_start_date`.
        """
        try:
            row = self.Config.read_row()  # ty: ignore[unresolved-attribute]
            if row is not None:
                val = row.get("lookback_period") if isinstance(row, dict) else getattr(row, "lookback_period", None)
                if val is not None and int(val) > 0:
                    return f"{int(val)} days ago"
        except Exception:
            logger.exception("_lookback_start_date: failed to read config")
        return f"{default_days} days ago"

    @abc.abstractmethod
    def resources(self, client: Any) -> list[Any]:
        """Return dlt @resource objects for this sync."""
        ...

    def build_client(self) -> Any:
        """Build an API client from stored credentials. Override for auth."""
        return None

    def cleanup_client(self, client: Any) -> None:
        """Clean up resources created by ``build_client``.

        Called in a ``finally`` block after sync completes (or fails).
        Override for sources that create temp files or hold connections.
        The default implementation does nothing.
        """

    @property
    def dataset_name(self) -> str:
        """DuckDB schema name for this source's raw data.

        All sources write to the ``sources`` schema. Table names are
        prefixed with the source name (e.g. ``sources.garmin_activities``).

        When ``current_entity_uuid`` is set to a non-primary entity, the
        schema is suffixed with ``__e<uuid8>`` so each entity's raw data
        lives in its own namespace.
        """
        from app.database import current_entity_uuid, current_user_id
        from app.local_users import LocalUser

        entity_uuid = current_entity_uuid.get()
        if entity_uuid is None:
            return "sources"
        user_id = current_user_id.get()
        user = LocalUser.get_by_id(user_id) if user_id else None
        if user and getattr(user, "uuid", None) == entity_uuid:
            return "sources"
        return f"e{entity_uuid[:8]}__sources"

    def acquire_sync_lock(self) -> bool:
        """Try to acquire the sync lock for this source. Returns False if already locked."""
        with self._sync_locks_guard:
            if self.name not in self._sync_locks:
                self._sync_locks[self.name] = threading.Lock()
        return self._sync_locks[self.name].acquire(blocking=False)

    def release_sync_lock(self) -> None:
        """Release the sync lock for this source."""
        with self._sync_locks_guard:
            lock = self._sync_locks.get(self.name)
        if lock is not None:
            with contextlib.suppress(RuntimeError):
                lock.release()

    def _mark_synced(self) -> None:
        """Update the synced_at timestamp in the plugin state table and data catalog."""
        try:
            inst = self.get_or_create_instance()
            inst.mark_synced()
            from app.pubsub import pubsub

            pubsub.publish_sync(
                "plugin_state_changed",
                {"kind": "source", "name": self.name, "synced_at": inst.synced_at, "enabled": inst.enabled},
            )
        except Exception:
            logger.exception("Failed to update synced_at for %s", self.name)
        try:
            from app.data_catalog import catalog

            catalog().mark_refreshed(self.name)
        except Exception:
            pass

    def sync(
        self,
        *,
        full_refresh: bool = False,
        on_progress: Callable[[str, str], None] | None = None,
        **_kwargs: Any,
    ) -> None:
        """Default sync: build_client -> resources -> run_sync -> transform -> mark synced.

        `on_progress`, if given, is forwarded to `run_sync` and called at each
        per-resource checkpoint so streaming consumers can surface progress.
        """
        from shenas_sources.core.cli import run_sync

        client = self.build_client()
        try:
            res = self.resources(client)
            # Build resource name -> display name map from table classes.
            rdn: dict[str, str] = {}
            try:
                from app.plugin import Plugin

                for t in Plugin.load_tables(self.name, kind="source"):
                    rdn[t._Meta.name] = getattr(t._Meta, "display_name", t._Meta.name)  # ty: ignore[unresolved-attribute]
            except AttributeError:
                pass
            run_sync(
                self.name,
                self.dataset_name,
                res,
                full_refresh,
                self._auto_transform,
                on_progress=on_progress,
                display_name=self.display_name,
                resource_display_names=rdn,
            )
            self._post_sync(full_refresh)
        finally:
            self.cleanup_client(client)

    def _post_sync(self, full_refresh: bool) -> None:
        """Run all post-sync hooks: AS-OF macros, entity projection, mark synced.

        Called at the end of :meth:`sync` and by custom sync overrides
        (Gmail, Google Takeout) to avoid duplicating the hook sequence.
        """
        from shenas_sources.core.as_of import apply_as_of_macros

        try:
            from app.database import cursor

            with cursor() as cur:
                apply_as_of_macros(cur, self.dataset_name)
        except Exception:
            logger.exception("Failed post-sync hooks for %s", self.name)
        try:
            self._project_entities()
            self._refresh_wide_views()
        except Exception:
            logger.exception("Failed entity projection for %s", self.name)
        try:
            self._ensure_timeseries_view()
        except Exception:
            logger.exception("Failed timeseries view for %s", self.name)
        self._mark_synced()
        self._log_sync_event(full_refresh)

    def _project_entities(self) -> None:
        """Post-sync hook: project raw source rows into statements.

        For each :class:`SourceTable` in this source's ``TABLES`` that
        declares ``entity_type`` + ``entity_projection``, scans the current
        SCD2 slice (or full table for non-SCD2 kinds) and:

        1. Upserts each row as an :class:`app.entity.Entity` row with a
           deterministic ``uuid`` derived from the type + natural PK.
        2. Upserts one statement per ``(column, property_id)`` mapping with
           ``source=<plugin_name>``, skipping NULL values.
        3. Registers referenced properties in ``entities.properties`` on
           first encounter (idempotent upsert).

        Statements are loaded plainly (not via dlt) because the projection
        set is small relative to the raw table and always represents the
        current truth of the entity.
        """

        from app.plugin import Plugin

        all_tables = list(Plugin.load_tables(self.name, kind="source"))
        if not all_tables:
            return

        # Load views from views.py (e.g. TileInfo) and ensure them.
        all_views = list(Plugin.load_views(self.name))
        for view in all_views:
            try:
                view.ensure()  # ty: ignore[unresolved-attribute]
            except Exception:
                logger.debug("View %s could not be ensured, skipping", getattr(getattr(view, "_Meta", None), "name", "?"))

        projectable = [
            relation
            for relation in [*all_tables, *all_views]
            if isinstance(relation, type)
            and getattr(getattr(relation, "_Meta", None), "entity_type", None)
            and getattr(getattr(relation, "_Meta", None), "entity_projection", None)
        ]
        if not projectable:
            return

        for relation in projectable:
            self._project_table(relation)

    def _project_table(self, t: type) -> None:
        """Project one source table's current rows into entities + statements.

        Projection entries can be:
        - **string** (property): maps column to a property on the row's entity.
          ``{"language": "P277"}`` -> Statement(entity, "P277", row.language).
        - **dict** (entity reference): the column value names a *different*
          entity.  ``{"city": {"entity_type": "city"}}`` -> upserts a city
          Entity whose name (and PK) is the column value.
        """
        from app.entities.properties import Property
        from app.entities.statements import Statement
        from app.entity import Entity, compute_entity_id

        type_name: str = t._Meta.entity_type  # ty: ignore[unresolved-attribute]
        name_col: str | None = getattr(t._Meta, "entity_name_column", None)  # ty: ignore[unresolved-attribute]
        raw_projection: dict[str, str | dict[str, str]] = dict(t._Meta.entity_projection)  # ty: ignore[unresolved-attribute]
        pk_cols_list = list(t._Meta.pk)  # ty: ignore[unresolved-attribute]

        # Split into property projections and entity reference projections.
        property_projection: dict[str, str] = {}
        entity_ref_projection: dict[str, str] = {}  # column -> entity_type
        for col, spec in raw_projection.items():
            if isinstance(spec, dict):
                entity_ref_projection[col] = spec["entity_type"]
            else:
                property_projection[col] = spec

        for pid in set(property_projection.values()):
            if Property.find(pid) is None:
                Property.from_row((pid, pid, "string", type_name, self.name, None, None)).insert()

        # t is a SourceTable subclass -- .all() handles SCD2 filtering
        # automatically for DimensionTable/SnapshotTable kinds.
        source_rows = t.all()  # ty: ignore[unresolved-attribute]

        for row in source_rows:
            pk_values = tuple(getattr(row, c) for c in pk_cols_list)
            if any(v in (None, "") for v in pk_values):
                continue
            entity_id = compute_entity_id(type_name, pk_values)
            entity_name = str(getattr(row, name_col, None) or pk_values[0]) if name_col else str(pk_values[0])

            existing_entity = Entity.find_by_uuid(entity_id)
            if existing_entity is None:
                Entity(
                    uuid=entity_id,
                    type=type_name,
                    name=entity_name,
                    status="disabled",
                ).insert()
            else:
                existing_entity.name = entity_name
                existing_entity.save()

            # Property statements on the row's own entity.
            for src_col, property_id in property_projection.items():
                self._upsert_property_statement(row, src_col, property_id, entity_id, Statement)

            # Entity reference columns: upsert referenced entities.
            for src_col, ref_type in entity_ref_projection.items():
                self._upsert_entity_ref(row, src_col, ref_type)

    def _upsert_property_statement(
        self, row: object, column: str, property_id: str, entity_id: str, statement_cls: type
    ) -> None:
        """Upsert a property statement on an entity from a row column value."""
        value = getattr(row, column, None)
        if value is None or value == "":
            return
        value_str = str(value)
        existing = statement_cls.find(entity_id, property_id, value_str)  # ty: ignore[unresolved-attribute]
        if existing is None:
            statement_cls.from_row((entity_id, property_id, value_str, value_str, "normal", None, self.name)).insert()  # ty: ignore[unresolved-attribute]
        else:
            existing.value_label = value_str
            existing.source = self.name
            existing.save()

    def _upsert_entity_ref(self, row: object, column: str, entity_type: str) -> None:
        """Upsert an entity referenced by a column value (e.g. city name).

        If the entity already exists (e.g. seeded by Wikidata) and is
        disabled, enable it -- the user's data references it, so it's
        relevant. Also creates a statement linking the entity to this
        source so it appears in the source's entities tab.
        """
        from app.entities.statements import Statement
        from app.entity import Entity, compute_entity_id

        ref_name = getattr(row, column, None)
        if not ref_name or str(ref_name).strip() == "":
            return
        ref_name_str = str(ref_name).strip()
        ref_id = compute_entity_id(entity_type, (ref_name_str,))
        existing = Entity.find_by_uuid(ref_id)
        if existing is None:
            Entity(
                uuid=ref_id,
                type=entity_type,
                name=ref_name_str,
                status="enabled",
            ).insert()
        elif existing.status == "disabled":
            existing.status = "enabled"
            existing.save()
        # Link entity to this source via a statement.
        property_id = f"referenced_by:{column}"
        if Statement.find(ref_id, property_id, self.name) is None:
            Statement.from_row((ref_id, property_id, self.name, self.name, "normal", None, self.name)).insert()

    def _ensure_timeseries_view(self) -> None:  # noqa: PLR0912, PLR0915
        """Post-sync hook: create or replace a ``{source}__timeseries`` wide view.

        Joins all time-series tables from this source into a single view
        bucketed to the auto-detected grain (day for all-DATE sources,
        hour for TIMESTAMP sources, year for INTEGER-year sources).
        Each table becomes a CTE aggregated to that grain, then all CTEs
        are FULL OUTER JOINed on ``time_bucket``.

        Columns are prefixed with the table's short name (without the source
        prefix) to avoid collisions: ``daily_stats__calories``, ``sleep__score``.
        """
        from shenas_sources.core.table import (
            AggregateTable,
            CounterTable,
            DimensionTable,
            EventTable,
            IntervalTable,
            M2MTable,
            SnapshotTable,
            SourceTable,
        )

        tables = list(getattr(type(self), "_source_tables", ()))
        if not tables:
            return

        schema = self.dataset_name
        view_name = f"{self.name}__timeseries"

        # Detect the natural grain from time-column db_types.
        # If all time columns are DATE, use 'day'. If any are TIMESTAMP,
        # use 'hour'. INTEGER columns (year/month) use 'year'.
        grain = SourceTable.detect_grain(tables, (EventTable, IntervalTable, AggregateTable, CounterTable))

        # Map db_type -> default SQL aggregation function
        agg_map = {
            "integer": "SUM",
            "bigint": "SUM",
            "double": "AVG",
            "float": "AVG",
            "real": "AVG",
            "boolean": "BOOL_OR",
            "varchar": "FIRST",
            "text": "FIRST",
            "timestamp": "MIN",
            "date": "MIN",
        }

        # Build per-table CTEs
        ctes: list[str] = []
        cte_names: list[str] = []
        skip_cols = {"id", "entity_id", "observed_at", "source", "source_device"}

        for table_cls in tables:
            meta = table_cls._Meta
            full_name = meta.name
            qualified = f'"{schema}"."{full_name}"'
            # Short name: strip the source prefix (garmin__daily_stats -> daily_stats)
            short = full_name.removeprefix(f"{self.name}__") if full_name.startswith(f"{self.name}__") else full_name

            time_col = table_cls.timeseries_time_col()
            if not time_col:
                continue

            # Get column metadata for aggregation
            try:
                import dataclasses
                from typing import get_type_hints

                from app.relation import Field as FieldMeta

                hints = get_type_hints(table_cls, include_extras=True)
                fields = dataclasses.fields(table_cls)
            except Exception:
                continue

            agg_cols: list[tuple[str, str, str]] = []
            for field in fields:
                col = field.name
                if col.startswith("_") or col in skip_cols or col == time_col:
                    continue
                if col in meta.pk:
                    continue
                # Skip time_end column for IntervalTable
                if issubclass(table_cls, IntervalTable) and col == getattr(meta, "time_end", None):
                    continue
                hint = hints.get(col)
                field_meta = FieldMeta.from_hint(hint) if hint else None
                db_type = field_meta.db_type.lower() if field_meta else "varchar"

                # Use explicit aggregation from Field, or fall back to db_type default
                if field_meta and field_meta.aggregation:
                    if field_meta.aggregation.lower() == "skip":
                        continue
                    agg_fn = field_meta.aggregation.upper()
                else:
                    agg_fn = agg_map.get(db_type, "FIRST")
                agg_cols.append((agg_fn, col, f"{short}__{col}"))

            if not agg_cols:
                continue

            # For SCD2 tables, filter to current slice
            where = ""
            if issubclass(table_cls, (DimensionTable, SnapshotTable, M2MTable)):
                where = " WHERE _dlt_valid_to IS NULL"

            cte_name = f"cte_{short}"
            cte_sql = table_cls.timeseries_cte(
                cte_name=cte_name,
                short=short,
                qualified=qualified,
                grain=grain,
                time_col=time_col,
                agg_exprs=agg_cols,
                where=where,
            )
            ctes.append(cte_sql)
            cte_names.append(cte_name)

        if not ctes:
            return

        # Build the final SELECT with FULL OUTER JOINs
        select_cols = ["COALESCE(" + ", ".join(f"{c}.time_bucket" for c in cte_names) + ") AS time_bucket"]
        select_cols.extend(f"{cte_name}.*" for cte_name in cte_names)

        # Build JOIN chain
        first = cte_names[0]
        join_clauses = [
            f"FULL OUTER JOIN {cte_name} ON {first}.time_bucket = {cte_name}.time_bucket" for cte_name in cte_names[1:]
        ]

        # Assemble the view DDL — use SELECT with explicit EXCLUDE to drop
        # the per-CTE time_bucket columns (we have the COALESCE'd one).
        excludes = ", ".join(f"{c}.time_bucket" for c in cte_names)

        cte_list = ",\n".join(ctes)
        coalesce_expr = ", ".join(f"{c}.time_bucket" for c in cte_names)
        star_cols = ", ".join(f"{c}.*" for c in cte_names)
        join_sql = "\n".join(join_clauses)
        view_sql = (
            f'CREATE OR REPLACE VIEW "{schema}"."{view_name}" AS\n'
            f"WITH {cte_list}\n"
            f"SELECT * EXCLUDE ({excludes})\n"
            f"FROM (SELECT COALESCE({coalesce_expr}) AS time_bucket, {star_cols}\n"
            f"FROM {first}\n"
            f"{join_sql})\n"
            f"ORDER BY time_bucket"
        )

        try:
            from app.database import cursor

            with cursor() as cur:
                cur.execute(view_sql)
            logger.info("Created timeseries view %s.%s (%d tables)", schema, view_name, len(ctes))
        except Exception:
            logger.exception("Failed to create timeseries view for %s", self.name)

    def _refresh_wide_views(self) -> None:
        """Post-sync hook: rebuild every per-type wide view.

        Statements added during this sync may introduce new property
        columns; the per-type ``entities.<type>s_wide`` views need a
        fresh ``CREATE OR REPLACE VIEW`` to reflect the expanded property
        set. Cheap (one DDL per type), safe to call unconditionally.
        """
        try:
            from app.entity import ensure_all_wide_views

            ensure_all_wide_views()
        except Exception:
            logger.exception("ensure_all_wide_views failed for %s", self.name)

    def run_sync_stream(self, *, full_refresh: bool = False) -> Iterator[tuple[str, str]]:
        """Run sync yielding (event, message) tuples for progress reporting.

        Runs the actual sync in a daemon worker thread and drains a queue from
        the generator body so per-resource progress events from `run_sync` flow
        out as they happen instead of all at once when sync completes.
        """
        import queue
        import threading

        from app.jobs import bind_job_id, get_job_id

        source_label = self.display_name or self.name
        logger.info("Sync started: %s", source_label)
        # No "starting sync" yield -- the spinner already shows the job is
        # running, and the next line is always "Fetching (1/N): ...".

        if self.has_auth and not self.is_authenticated:
            msg = "Not authenticated. Configure credentials in the Auth tab."
            logger.warning("Sync skipped: %s -- %s", source_label, msg)
            yield ("error", msg)
            return

        # Pre-check: try building the client to catch config errors early
        # without a full traceback in the logs.
        try:
            pre_client = self.build_client()
            self.cleanup_client(pre_client)
        except Exception as exc:
            msg = str(exc)
            logger.warning("Sync skipped: %s -- %s", source_label, msg)
            yield ("error", msg)
            return

        # ContextVars don't propagate across threading.Thread boundaries -- capture
        # the parent's job_id and rebind inside the worker so logs emitted from the
        # sync thread also carry it.
        job_id = get_job_id()
        q: queue.Queue[tuple[str, str] | None] = queue.Queue()

        def _worker() -> None:
            with bind_job_id(job_id):
                try:
                    self.sync(full_refresh=full_refresh, on_progress=lambda e, m: q.put((e, m)))
                    q.put(("__done__", f"Sync complete: {source_label}"))
                except Exception as exc:
                    logger.exception("Sync failed: %s", source_label)
                    q.put(("__error__", str(exc)))
                finally:
                    q.put(None)  # sentinel: end-of-stream

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        while True:
            try:
                item = q.get(timeout=0.5)
            except queue.Empty:
                if not t.is_alive():
                    break
                continue
            if item is None:  # sentinel
                break
            evt, msg = item
            if evt == "__done__":
                logger.info("Sync complete: %s", source_label)
                yield ("complete", msg)
            elif evt == "__error__":
                yield ("error", msg)
                return
            else:
                # fetch_start / fetch_done / flush / transform_start -- all "progress"
                yield ("progress", msg)
        # Daemon thread exits with the process; nothing to join. We can't cancel
        # an in-flight dlt run cleanly anyway.

    def _log_sync_event(self, full_refresh: bool) -> None:
        """Append a sync event to the mesh sync log."""
        try:
            from app.mesh.sync_log import append_event

            append_event(
                table_schema=self.name,
                table_name="*",
                operation="full_refresh" if full_refresh else "sync",
            )
        except Exception:
            pass  # mesh not initialized yet

    def _auto_transform(self) -> None:
        """Seed and run transforms via the Transform plugin system."""
        from shenas_transformers.core import Transformer
        from shenas_transformers.core.transform import Transform

        for cls in Transformer.load_all():
            plugin = cls()
            inst = plugin.instance()
            if not inst or inst.enabled:
                plugin.seed_defaults_for_source(self.name)

        count = Transform.run_for_source(self.name)
        logger.info("Transforms done: %s (%d)", self.name, count)

    # -- Auth flow ------------------------------------------------------------

    def authenticate(self, credentials: dict[str, str]) -> None:
        """Handle credential submission. Override for auth."""

    def complete_mfa(self, state: dict[str, Any], mfa_code: str) -> None:
        """Complete a multi-step MFA flow. Override if needed."""
        msg = f"{self.name} does not support MFA"
        raise NotImplementedError(msg)

    def get_pending_mfa_state(self) -> dict[str, Any] | None:
        """Return pending MFA state, or None. Override if source supports MFA."""
        return None

    @property
    def stored_credentials(self) -> list[str]:
        """Labels for stored credential fields that have values."""
        if not self.has_auth:
            return []
        try:
            row = self.Auth.read_row()  # ty: ignore[unresolved-attribute]
            columns = self.Auth.column_metadata()  # ty: ignore[unresolved-attribute]
            return [
                col["name"].replace("_", " ").title()
                for col in columns
                if col["name"] != "id" and row and row.get(col["name"])
            ]
        except Exception:
            return []

    # -- OAuth redirect flow (new) --

    @property
    def supports_oauth_redirect(self) -> bool:
        """True if this source supports the server-side OAuth redirect flow."""
        return False

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:
        """Generate an OAuth authorization URL. Override for OAuth sources.

        ``credentials`` may contain user-provided values (client_id, etc.)
        collected from auth_fields before the redirect.
        ``redirect_uri`` is the server callback URL the provider should return to.
        Returns the full authorization URL to redirect the browser to.
        """
        msg = f"{self.name} does not support OAuth redirect flow"
        raise NotImplementedError(msg)

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:
        """Exchange an auth code for tokens and store them. Override for OAuth sources."""
        msg = f"{self.name} does not support OAuth redirect flow"
        raise NotImplementedError(msg)

    def handle_auth(self, credentials: dict[str, str], *, redirect_uri: str | None = None) -> dict[str, Any]:  # noqa: PLR0911
        """Dispatch auth flow. Returns a result dict for the API response.

        Result keys: ok, message, error, needs_mfa, oauth_url, oauth_redirect.
        """
        # MFA completion
        if "mfa_code" in credentials:
            state = self.get_pending_mfa_state()
            if state is None:
                return {"ok": False, "error": "No pending MFA session. Start auth again."}
            try:
                self.complete_mfa(state, credentials["mfa_code"])
                return {"ok": True, "message": f"Authenticated {self.name}"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        # OAuth redirect flow (new)
        if self.supports_oauth_redirect and redirect_uri:
            try:
                url = self.start_oauth(redirect_uri, credentials or None)
                return {"ok": False, "oauth_redirect": url, "message": "Redirecting to authorize..."}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        # Legacy OAuth completion (auth_complete flag)
        if "auth_complete" in credentials:
            try:
                self.authenticate(credentials)
                return {"ok": True, "message": f"Authenticated {self.name}"}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        # Initial auth (API key, email/password, or legacy OAuth)
        try:
            self.authenticate(credentials)
            return {"ok": True, "message": f"Authenticated {self.name}"}
        except ValueError as exc:
            msg = str(exc)
            if "MFA code required" in msg:
                return {"ok": False, "needs_mfa": True, "message": "MFA code required"}
            if msg.startswith("OAUTH_URL:"):
                return {
                    "ok": False,
                    "oauth_url": msg.removeprefix("OAUTH_URL:"),
                    "message": "Open this URL in your browser to authorize",
                }
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_field_meta(f: dataclasses.Field) -> dict[str, Any]:  # type: ignore[type-arg]
    """Extract Field metadata from an Annotated dataclass field."""
    from app.table import Field

    hints = getattr(f.type, "__metadata__", ()) if hasattr(f.type, "__metadata__") else ()
    # Unwrap Optional[Annotated[...]]
    if not hints and hasattr(f.type, "__args__"):
        for arg in f.type.__args__:  # ty: ignore[not-iterable]
            if hasattr(arg, "__metadata__"):
                hints = arg.__metadata__
                break
    for h in hints:
        if isinstance(h, Field):
            return dataclasses.asdict(h)
    return {}
