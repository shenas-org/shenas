"""GraphQL Query resolvers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import strawberry
from strawberry.scalars import JSON  # noqa: TC002 - needed at runtime by Strawberry

from app.graphql.types import (
    AuthFieldsType,
    DBStatusType,
    PluginInfoType,
    ScheduleInfoType,
    TableEntry,
    ThemeInfo,
    TransformType,
)

if TYPE_CHECKING:
    from shenas_transformations.core.instance import TransformInstance


def _transform_to_gql(t: TransformInstance) -> TransformType:
    return TransformType(
        id=t.id,
        transform_type=t.transform_type,
        source_duckdb_schema=t.source_duckdb_schema,
        source_duckdb_table=t.source_duckdb_table,
        target_duckdb_schema=t.target_duckdb_schema,
        target_duckdb_table=t.target_duckdb_table,
        source_plugin=t.source_plugin,
        params=t.params or "{}",
        description=t.description or "",
        is_default=bool(t.is_default),
        enabled=bool(t.enabled),
        added_at=t.added_at,
        updated_at=t.updated_at,
        status_changed_at=t.status_changed_at,
    )


@strawberry.type
class Query:
    # -- Tables (Arrow IPC query endpoint stays REST, but table listing is here) --

    @strawberry.field
    def tables(self) -> list[TableEntry]:
        from app.db import cursor

        with cursor() as cur:
            rows = cur.execute(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema NOT IN ('information_schema', 'main') "
                "AND table_schema NOT LIKE '%\\_staging' ESCAPE '\\' "
                "ORDER BY table_schema, table_name"
            ).fetchall()
        return [TableEntry(schema_name=r[0], table=r[1]) for r in rows]

    # -- Auth --

    @strawberry.field
    def auth_fields(self, pipe: str) -> AuthFieldsType:
        from app.api.auth import auth_fields

        result = auth_fields(pipe)
        return AuthFieldsType.from_pydantic(result)  # ty: ignore[unresolved-attribute]

    # -- Config --

    @strawberry.field
    def config_value(self, kind: str, name: str, key: str) -> str | None:
        from app.api.sources import _load_plugin

        try:
            cls = _load_plugin(kind, name)
            if not cls:
                return None
            val = cls().get_config_value(key)
            return str(val) if val is not None else None
        except Exception:
            return None

    # -- Database --

    @strawberry.field
    def db_status(self) -> DBStatusType:
        from app.api.db import db_status

        return DBStatusType.from_pydantic(db_status())  # ty: ignore[unresolved-attribute]

    @strawberry.field
    def device_name(self) -> str:
        try:
            from app.mesh.identity import get_device_info

            return get_device_info()["device_name"]
        except Exception:
            return ""

    @strawberry.field
    def db_tables(self) -> JSON:
        from app.api.db import db_tables

        return db_tables()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def schema_tables(self) -> JSON:
        from app.api.db import schema_plugin_tables

        return schema_plugin_tables()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def schema_plugins(self) -> JSON:
        from app.api.db import schema_plugin_ownership

        return schema_plugin_ownership()  # ty: ignore[invalid-return-type]

    # -- Plugins --

    @strawberry.field
    def plugin_kinds(self) -> JSON:
        """Return all discovered plugin kinds with display labels, ordered by label."""
        from app.api.sources import _load_plugins
        from shenas_plugins.core.plugin import VALID_KINDS, Plugin

        plural_map: dict[str, str] = {}
        for kind in VALID_KINDS:
            try:
                for cls in _load_plugins(kind, base=Plugin):
                    plural = getattr(cls, "display_name_plural", None)
                    if plural:
                        plural_map[kind] = plural
                        break
            except Exception:
                pass

        kinds = [{"id": k, "label": plural_map.get(k, f"{k.title()}s")} for k in sorted(VALID_KINDS)]
        return sorted(kinds, key=lambda x: x["label"])  # ty: ignore[invalid-return-type]

    @strawberry.field
    def plugins(self, kind: str) -> list[PluginInfoType]:
        from app.models import ConfigEntry, PluginInfo
        from shenas_plugins.core.plugin import Plugin

        items = []
        for pi in Plugin.list_installed(kind):
            config_entries = [
                ConfigEntry(
                    key=str(e["key"]),
                    label=str(e.get("label") or ""),
                    value=e.get("value"),
                    description=str(e.get("description") or ""),
                )
                for e in pi.get("config_entries", [])
            ]
            items.append(
                PluginInfoType.from_pydantic(  # ty: ignore[unresolved-attribute]
                    PluginInfo(
                        name=pi.get("name", ""),
                        display_name=pi.get("display_name", ""),
                        package=pi.get("package", ""),
                        version=pi.get("version", ""),
                        signature=pi.get("signature", ""),
                        description=pi.get("description", ""),
                        commands=pi.get("commands", []),
                        enabled=pi.get("enabled", True),
                        has_config=pi.get("has_config", False),
                        has_data=pi.get("has_data", False),
                        has_auth=pi.get("has_auth", False),
                        is_authenticated=pi.get("is_authenticated"),
                        sync_frequency=pi.get("sync_frequency"),
                        config_entries=config_entries,
                        added_at=pi.get("added_at"),
                        updated_at=pi.get("updated_at"),
                        status_changed_at=pi.get("status_changed_at"),
                        synced_at=pi.get("synced_at"),
                    )
                )
            )
        return items

    @strawberry.field
    def plugin_info(self, kind: str, name: str) -> JSON:
        from app.api.sources import _load_plugin, _load_plugin_fresh

        cls = _load_plugin(kind, name) or _load_plugin_fresh(kind, name)
        if not cls:
            return {"name": name, "kind": kind, "display_name": name.replace("-", " ").title()}  # ty: ignore[invalid-return-type]
        return cls().get_info()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def available_plugins(self, kind: str) -> list[str]:
        """List plugin names available on the repository server for a given kind."""
        import re
        from html.parser import HTMLParser
        from urllib.request import urlopen

        from shenas_plugins.core.plugin import DEFAULT_INDEX

        prefix = f"shenas-{kind}-"
        try:
            with urlopen(f"{DEFAULT_INDEX}/simple/", timeout=5) as resp:
                html = resp.read().decode()
        except Exception:
            return []

        names: list[str] = []

        class _Parser(HTMLParser):
            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                if tag == "a":
                    for attr_name, val in attrs:
                        if attr_name == "href" and val:
                            pkg = val.strip("/").split("/")[-1]
                            if pkg.startswith(prefix) and pkg != f"{prefix}core":
                                names.append(re.sub(r"[-_]+", "-", pkg.removeprefix(prefix)))

        _Parser().feed(html)
        return sorted(set(names))

    # -- Sync --

    @strawberry.field
    def sync_schedule(self) -> list[ScheduleInfoType]:
        from app.api.sources import _load_plugins
        from app.models import ScheduleInfo
        from shenas_sources.core.source import Source

        result = []
        for cls in _load_plugins("source", base=Source, include_internal=False):
            src = cls()
            freq = src.sync_frequency
            if freq is None:
                continue
            s = src.instance()
            if not s or not s.enabled:
                continue
            result.append(
                ScheduleInfoType.from_pydantic(  # ty: ignore[unresolved-attribute]
                    ScheduleInfo(
                        name=src.name,
                        sync_frequency=freq,
                        synced_at=s.synced_at,
                        is_due=src.is_due_for_sync,
                    )
                )
            )
        return sorted(result, key=lambda x: x.name)

    # -- Transforms --

    @strawberry.field
    def transform_types(self) -> JSON:
        """Return available transform plugin types with their param schemas."""
        from importlib.metadata import entry_points

        result = []
        for ep in entry_points(group="shenas.transformations"):
            try:
                cls = ep.load()
                inst = cls()
                schema = inst.param_schema() if hasattr(inst, "param_schema") else []
                result.append(
                    {
                        "name": ep.name,
                        "displayName": getattr(inst, "display_name", ep.name),
                        "description": getattr(inst, "description", ""),
                        "paramSchema": schema,
                    }
                )
            except Exception:
                pass
        return sorted(result, key=lambda x: x["displayName"])  # ty: ignore[invalid-return-type]

    @strawberry.field
    def table_columns(self, schema: str, table: str) -> list[str]:
        """Return column names for a DuckDB table."""
        from app.db import cursor

        with cursor() as cur:
            rows = cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                [schema, table],
            ).fetchall()
        return [r[0] for r in rows]

    @strawberry.field
    def transforms(self, source: str | None = None) -> list[TransformType]:
        from shenas_transformations.core.instance import TransformInstance

        rows = TransformInstance.for_plugin(source) if source else TransformInstance.all(order_by="id")
        return [_transform_to_gql(t) for t in rows]

    @strawberry.field
    def transform(self, transform_id: int) -> TransformType | None:
        from shenas_transformations.core.instance import TransformInstance

        t = TransformInstance.find(transform_id)
        return _transform_to_gql(t) if t else None

    # -- Theme --

    @strawberry.field
    def theme(self) -> ThemeInfo:
        from app.main import _get_active_theme

        t = _get_active_theme()
        if t:
            return ThemeInfo(name=t.name, css=f"/themes/{t.name}/{t.css}")
        return ThemeInfo(name=None, css=None)

    # -- App-level --

    @strawberry.field
    def hotkeys(self, info: strawberry.types.Info) -> JSON:  # noqa: ARG002
        from app.hotkeys import Hotkey

        return Hotkey.get_all()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def workspace(self, info: strawberry.types.Info) -> JSON:  # noqa: ARG002
        from app.workspace import Workspace

        return Workspace.get()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def dashboards(self) -> JSON:
        from app.api.sources import _load_dashboards
        from shenas_plugins.core.plugin import PluginInstance

        result = []
        for c in _load_dashboards(include_internal=False):
            inst = PluginInstance.find("dashboard", c.name)
            if inst is not None and not inst.enabled:
                continue
            result.append(
                {
                    "name": c.name,
                    "display_name": c.display_name,
                    "tag": c.tag,
                    "js": f"/dashboards/{c.name}/{c.entrypoint}",
                    "description": c.description,
                }
            )
        return result  # ty: ignore[invalid-return-type]

    @strawberry.field
    def dependencies(self) -> JSON:
        from importlib.metadata import distributions

        prefixes = {
            "shenas-source-": "source",
            "shenas-dataset-": "dataset",
            "shenas-dashboard-": "dashboard",
            "shenas-model-": "model",
            "shenas-frontend-": "frontend",
            "shenas-theme-": "theme",
        }
        result: dict[str, list[str]] = {}
        for dist in distributions():
            pkg_name = dist.metadata["Name"]
            if pkg_name.endswith("-core"):
                continue
            kind = None
            plugin_name = ""
            for prefix, k in prefixes.items():
                if pkg_name.startswith(prefix):
                    kind = k
                    plugin_name = pkg_name.removeprefix(prefix)
                    break
            if not kind:
                continue
            deps = []
            for req in dist.requires or []:
                req_name = req.split(";")[0].split("[")[0].split(">")[0].split("<")[0].split("=")[0].split("!")[0].strip()
                for dep_prefix, dep_kind in prefixes.items():
                    if req_name.startswith(dep_prefix) and not req_name.endswith("-core"):
                        deps.append(f"{dep_kind}:{req_name.removeprefix(dep_prefix)}")
            if deps:
                result[f"{kind}:{plugin_name}"] = deps
        return result  # ty: ignore[invalid-return-type]

    # -- Models --

    @strawberry.field
    def models(self) -> JSON:
        from shenas_models.core import Model  # ty: ignore[unresolved-import]

        from app.api.sources import _load_plugins

        return sorted(  # ty: ignore[invalid-return-type]
            [cls().get_info() for cls in _load_plugins("model", base=Model, include_internal=False)],
            key=lambda x: x["name"],
        )

    @strawberry.field
    def model_status(self, name: str) -> JSON:
        from app.api.sources import _load_plugin

        cls = _load_plugin("model", name)
        if not cls:
            return {"name": name, "available": False, "round": None}  # ty: ignore[invalid-return-type]
        return cls().training_status  # ty: ignore[unresolved-attribute]

    @strawberry.field
    def model_predict(self, name: str) -> JSON:
        from app.api.sources import _load_plugin

        cls = _load_plugin("model", name)
        if not cls:
            return None  # ty: ignore[invalid-return-type]
        return cls().predict()  # ty: ignore[unresolved-attribute]

    # -- Analytics catalog --
    #
    # Single read-only query that returns the structured metadata for every
    # source-side raw table and every dataset-side metric table that is
    # currently installed. The LLM uses this to know what columns exist,
    # what kind each table is (so it can pick the right operation), and
    # which AS-OF macros to call for SCD2 lookups. System tables (Hypothesis,
    # Transform, Hotkey, Workspace, PluginInstance) are intentionally
    # excluded -- they are not joinable analytical inputs.

    @strawberry.field
    def catalog(self) -> JSON:
        """Return ``[table_metadata]`` for every queryable source / metric table.

        Thin wrapper over :func:`app.analytics_catalog.walk_catalog`,
        which both this query and the recipe runner share.
        """
        from app.analytics_catalog import walk_catalog

        return walk_catalog()  # ty: ignore[invalid-return-type]

    # -- Analysis modes --

    @strawberry.field
    def analysis_modes(self) -> JSON:
        """Return metadata for all registered analysis modes."""
        from app.api.sources import _discover_analyses
        from shenas_plugins.core.analytics.mode import list_modes

        _discover_analyses()
        return list_modes()  # ty: ignore[invalid-return-type]

    # -- Literature --

    @strawberry.field
    def literature_findings(self, limit: int | None = None) -> JSON:
        """Return stored literature findings."""
        from app.literature import Finding

        rows = Finding.all(order_by="id DESC", limit=limit)
        return [f.to_prompt_line() for f in rows]  # ty: ignore[invalid-return-type]

    @strawberry.field
    def suggested_hypotheses(self, limit: int = 10) -> JSON:
        """Return proactive hypothesis suggestions from literature cross-referenced with installed data."""
        from app.analytics_catalog import catalog_by_qualified_name
        from app.literature import suggest_hypotheses

        catalog = catalog_by_qualified_name()
        return [s.model_dump() for s in suggest_hypotheses(catalog, limit=limit)]  # ty: ignore[invalid-return-type]

    # -- Hypotheses --
    #
    # Read-only listing + single fetch over the Hypothesis system table.
    # The mutations that create / run / promote hypotheses live in
    # app/graphql/mutations.py.

    # -- Suggestions --
    #
    # Read-only listing of LLM-suggested datasets, transforms, and analyses.

    @strawberry.field
    def suggested_datasets(self) -> JSON:
        """Return all suggested (not yet accepted) datasets."""
        from shenas_plugins.core.plugin import PluginInstance

        return [  # ty: ignore[invalid-return-type]
            {
                "name": pi.name,
                "is_suggested": pi.is_suggested,
                "enabled": pi.enabled,
                **(pi.metadata or {}),
            }
            for pi in PluginInstance.suggested("dataset")
        ]

    @strawberry.field
    def suggested_transforms(self, source: str | None = None) -> JSON:
        """Return all suggested (not yet accepted) transforms."""
        from shenas_transformations.core.instance import TransformInstance

        rows = TransformInstance.suggested(source)
        return [  # ty: ignore[invalid-return-type]
            {
                "id": t.id,
                "source": f"{t.source_duckdb_schema}.{t.source_duckdb_table}",
                "target": f"{t.target_duckdb_schema}.{t.target_duckdb_table}",
                "source_plugin": t.source_plugin,
                "description": t.description or "",
                "params": t.get_params(),
            }
            for t in rows
        ]

    @strawberry.field
    def suggested_analyses(self) -> JSON:
        """Return all suggested (not yet accepted) analysis hypotheses."""
        from app.hypotheses import Hypothesis

        return [  # ty: ignore[invalid-return-type]
            {
                "id": h.id,
                "question": h.question,
                "rationale": h.plan or "",
                "datasets_involved": (h.inputs or "").split(",") if h.inputs else [],
                "complexity": h.mode or "",
                "created_at": str(h.created_at) if h.created_at else None,
            }
            for h in Hypothesis.suggested()
        ]

    # -- Hypotheses --
    #
    # Read-only listing + single fetch over the Hypothesis system table.
    # The mutations that create / run / promote hypotheses live in
    # app/graphql/mutations.py.

    @strawberry.field
    def hypotheses(self, limit: int | None = None) -> JSON:
        """Return every hypothesis row, most recent first."""
        from app.hypotheses import Hypothesis

        return [_hypothesis_to_dict(h) for h in Hypothesis.all(order_by="created_at DESC", limit=limit)]  # ty: ignore[invalid-return-type]

    @strawberry.field
    def hypothesis(self, hypothesis_id: int) -> JSON:
        """Return one hypothesis by id, or ``None`` if not found."""
        from app.hypotheses import Hypothesis

        h = Hypothesis.find(hypothesis_id)
        return _hypothesis_to_dict(h) if h else None  # ty: ignore[invalid-return-type]


def _hypothesis_to_dict(h: Any) -> dict[str, Any]:
    """Serialize a Hypothesis row to a JSON-friendly dict for GraphQL."""
    result = h.result()
    return {
        "id": h.id,
        "question": h.question,
        "plan": h.plan or "",
        "inputs": (h.inputs or "").split(",") if h.inputs else [],
        "interpretation": h.interpretation or "",
        "model": h.model or "",
        "mode": h.mode or "hypothesis",
        "promoted_to": h.promoted_to,
        "parent_id": getattr(h, "parent_id", None),
        "created_at": str(h.created_at) if h.created_at else None,
        "recipe": _safe_json_load(h.recipe_json),
        "result": result.model_dump() if result is not None else None,
    }


def _safe_json_load(s: str) -> Any:
    import json

    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None
