"""GraphQL Query resolvers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import strawberry
from strawberry.scalars import JSON  # noqa: TC002 - needed at runtime by Strawberry

from app.graphql.types import (
    AuthFieldsType,
    CategorySetType,
    CategoryValueType,
    ColumnInfoType,
    ConfigEntryType,
    DashboardType,
    DataResourceType,
    DependencyEdge,
    EntityRelationshipTypeType,
    EntityTypeType,
    FreshnessInfoType,
    GqlEntityRelationshipType,
    GqlEntityType,
    HypothesisType,
    ModelInfoType,
    ParamFieldType,
    PluginInfoType,
    PropertyType,
    QualityCheckType,
    QualityInfoType,
    ScheduleInfoType,
    SuggestedAnalysisType,
    SuggestedDatasetType,
    TableEntry,
    ThemeInfo,
    TimeColumnsInfoType,
    TransformerInfoType,
    TransformStepType,
    TransformType,
)

if TYPE_CHECKING:
    from shenas_transformers.core.transform import Transform

    from app.data_catalog import DataResource
    from app.plugin import Plugin


def _plugin_to_gql(plugin: Plugin) -> PluginInfoType:
    from app.models import PluginInfo

    return PluginInfoType.from_pydantic(  # ty: ignore[unresolved-attribute]
        PluginInfo(
            name=plugin.name,
            display_name=getattr(plugin, "display_name", plugin.name),
            description=getattr(plugin, "description", ""),
        ),
    )


def _data_resource_to_gql(resource: DataResource) -> DataResourceType:
    meta = resource.metadata_dict
    time_raw = meta.get("time_columns") or {}
    columns_raw = meta.get("columns") or []
    return DataResourceType(
        id=resource.id,
        schema_name=resource.ref.schema,
        table_name=resource.ref.table,
        display_name=resource.display_name,
        description=resource.effective_description,
        plugin=_plugin_to_gql(resource.plugin),
        kind=meta.get("kind"),
        query_hint=meta.get("query_hint"),
        as_of_macro=meta.get("as_of_macro"),
        primary_key=meta.get("primary_key", []),
        columns=[
            ColumnInfoType(
                name=column.get("name", ""),
                db_type=column.get("db_type", ""),
                nullable=column.get("nullable", True),
                description=column.get("description", ""),
                unit=column.get("unit"),
                value_range=list(column["value_range"]) if column.get("value_range") else None,
                example_value=str(column["example_value"]) if column.get("example_value") is not None else None,
                interpretation=column.get("interpretation"),
            )
            for column in columns_raw
        ],
        time_columns=TimeColumnsInfoType(
            time_at=time_raw.get("time_at"),
            time_start=time_raw.get("time_start"),
            time_end=time_raw.get("time_end"),
            cursor_column=time_raw.get("cursor_column"),
            observed_at_injected=time_raw.get("observed_at_injected", False),
        ),
        freshness=FreshnessInfoType(
            last_refreshed=resource.last_refreshed,
            sla_minutes=resource.freshness_sla_minutes,
            is_stale=resource.is_stale,
        ),
        quality=QualityInfoType(
            expected_row_count_min=resource.expected_row_count_min,
            expected_row_count_max=resource.expected_row_count_max,
            actual_row_count=resource.actual_row_count,
            latest_checks=[
                QualityCheckType(
                    check_type=check.check_type,
                    status=check.status,
                    message=check.message,
                    value=check.value,
                    checked_at=check.checked_at,
                )
                for check in resource.quality_checks
            ],
        ),
        user_notes=resource.user_notes,
        tags=resource.tags,
        upstream_transforms=[_transform_to_gql(transform) for transform in resource.upstream_transforms]
        if resource.upstream_transforms is not None
        else None,
        downstream_transforms=[_transform_to_gql(transform) for transform in resource.downstream_transforms]
        if resource.downstream_transforms is not None
        else None,
    )


def _stub_resource(ref: Any) -> DataResourceType:
    """Minimal stub for a resource that isn't in the catalog (e.g. stale ref)."""
    from app.models import PluginInfo

    return DataResourceType(
        id=ref.id if ref else "",
        schema_name=ref.schema if ref else "",
        table_name=ref.table if ref else "",
        display_name=ref.table if ref else "(unknown)",
        description="",
        plugin=PluginInfoType.from_pydantic(PluginInfo(name="", display_name="")),  # ty: ignore[unresolved-attribute]
        primary_key=[],
        columns=[],
        time_columns=TimeColumnsInfoType(),
        freshness=FreshnessInfoType(),
        quality=QualityInfoType(latest_checks=[]),
        tags=[],
    )


def _transformer_info(transformer_name: str) -> TransformerInfoType:
    from app.plugin import Plugin

    try:
        for cls in Plugin.load_by_kind("transformer"):
            if getattr(cls, "name", "") == transformer_name:
                inst = cls()
                return TransformerInfoType(
                    name=transformer_name,
                    display_name=getattr(cls, "display_name", transformer_name),
                    description=getattr(cls, "description", ""),
                    param_schema=[ParamFieldType(**p) for p in inst.param_schema()],  # ty: ignore[unresolved-attribute]
                )
    except Exception:
        pass
    return TransformerInfoType(
        name=transformer_name,
        display_name=transformer_name,
        param_schema=[],
    )


def _transform_to_gql(
    t: Transform,
    *,
    resource_map: dict[str, Any] | None = None,
) -> TransformType:
    if resource_map:
        source_r = resource_map.get(t.source_ref.id)
        target_r = resource_map.get(t.target_ref.id)
    else:
        from app.data_catalog import catalog

        source_r = catalog().get_resource(t.source_ref.id)
        target_r = catalog().get_resource(t.target_ref.id)

    steps = [
        TransformStepType(
            id=step.id,
            ordinal=step.ordinal,
            transformer=_transformer_info(step.transformer),
            params=step.params or "{}",
            description=step.description or "",
        )
        for step in t.steps
    ]

    return TransformType(
        id=t.id,
        transform_type=t.transform_type,
        source=_data_resource_to_gql(source_r) if source_r else _stub_resource(t.source_ref),
        target=_data_resource_to_gql(target_r) if target_r else _stub_resource(t.target_ref),
        source_plugin=t.source_plugin,
        params=t.params or "{}",
        description=t.description or "",
        is_default=bool(t.is_default),
        enabled=bool(t.enabled),
        added_at=t.added_at,
        updated_at=t.updated_at,
        status_changed_at=t.status_changed_at,
        materialization=t.materialization or "table",
        steps=steps,
    )


@strawberry.type
class Query:
    # -- Tables (Arrow IPC query endpoint stays REST, but table listing is here) --

    @strawberry.field
    def tables(self) -> list[TableEntry]:
        from app.database import cursor

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
    def auth_fields(self, source: str) -> AuthFieldsType:
        from app.api.auth import auth_fields

        result = auth_fields(source)
        return AuthFieldsType.from_pydantic(result)  # ty: ignore[unresolved-attribute]

    # -- Config --

    @strawberry.field
    def config_value(self, kind: str, name: str, key: str) -> str | None:
        from app.plugin import Plugin

        try:
            cls = Plugin.load_by_name_and_kind(name, kind)
            if not cls:
                return None
            val = cls().get_config_value(key)
            return str(val) if val is not None else None
        except Exception:
            return None

    @strawberry.field
    def device_name(self) -> str:
        try:
            from app.mesh.identity import get_device_info

            return get_device_info()["device_name"]
        except Exception:
            return ""

    # -- Plugins --

    @strawberry.field
    def plugin_kinds(self) -> JSON:
        """Return all discovered plugin kinds with display labels, ordered by label."""
        from app.plugin import VALID_KINDS, Plugin

        plural_map: dict[str, str] = {}
        for kind in VALID_KINDS:
            try:
                for cls in Plugin.load_by_kind(kind):
                    plural = getattr(cls, "display_name_plural", None)
                    if plural:
                        plural_map[kind] = plural
                        break
            except Exception:
                pass

        kinds = [
            {
                "id": k,
                "label": plural_map.get(k, f"{k.title()}s"),
                "display_name": plural_map.get(k, f"{k.title()}s"),
            }
            for k in sorted(VALID_KINDS)
        ]
        return sorted(kinds, key=lambda x: x["label"])  # ty: ignore[invalid-return-type]

    @strawberry.field
    def plugins(self, kind: str) -> list[PluginInfoType]:
        from app.api.db import schema_plugin_ownership
        from app.models import ConfigEntry, PluginInfo
        from app.plugin import Plugin

        ownership = schema_plugin_ownership()
        plugin_rows = Plugin.compute_plugin_rows()

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
            name = pi.get("name", "")
            items.append(
                PluginInfoType.from_pydantic(  # ty: ignore[unresolved-attribute]
                    PluginInfo(
                        name=name,
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
                        has_entities=pi.get("has_entities", False),
                        is_authenticated=pi.get("is_authenticated"),
                        sync_frequency=pi.get("sync_frequency"),
                        entity_types=pi.get("entity_types", []),
                        entity_uuids=pi.get("entity_uuids", []),
                        tables=ownership.get(name, []),
                        total_rows=plugin_rows.get(name, 0),
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
    def plugin_config(self, kind: str, name: str) -> list[ConfigEntryType]:
        """Config entries for a single plugin. Fast -- no subprocess, no full listing."""
        from app.models import ConfigEntry
        from app.plugin import Plugin

        cls = Plugin.load_by_name_and_kind(name, kind) or Plugin._load_fresh(kind, name)
        if not cls:
            return []
        plugin = cls()
        if not plugin.has_config:
            return []
        return [
            ConfigEntryType.from_pydantic(  # ty: ignore[unresolved-attribute]
                ConfigEntry(
                    key=str(entry["key"]),
                    label=str(entry.get("label") or ""),
                    value=entry.get("value"),
                    description=str(entry.get("description") or ""),
                    ui_widget=str(entry.get("ui_widget") or ""),
                    default_value=entry.get("default_value"),
                )
            )
            for entry in plugin.get_config_entries()
        ]

    @strawberry.field
    def plugin_info(self, kind: str, name: str) -> JSON:
        from app.plugin import Plugin

        cls = Plugin.load_by_name_and_kind(name, kind) or Plugin._load_fresh(kind, name)
        if not cls:
            return {"name": name, "kind": kind, "display_name": name.replace("-", " ").title()}  # ty: ignore[invalid-return-type]
        return cls().get_info()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def available_plugins(self, kind: str) -> list[str]:
        """List plugin names available on the repository server for a given kind."""
        from app.plugin import Plugin

        return Plugin.available_by_kind(kind)

    # -- Sync --

    @strawberry.field
    def sync_schedule(self) -> list[ScheduleInfoType]:
        from app.models import ScheduleInfo
        from shenas_sources.core.source import Source

        result = []
        for cls in Source.load_all(include_internal=False):
            source = cls()
            freq = source.sync_frequency
            if freq is None:
                continue
            s = source.instance()
            if not s or not s.enabled:
                continue
            result.append(
                ScheduleInfoType.from_pydantic(  # ty: ignore[unresolved-attribute]
                    ScheduleInfo(
                        name=source.name,
                        sync_frequency=freq,
                        synced_at=s.synced_at,
                        is_due=source.is_due_for_sync,
                    )
                )
            )
        return sorted(result, key=lambda x: x.name)

    # -- Transforms --

    @strawberry.field
    def transform_types(self) -> list[TransformerInfoType]:
        """Return available transformer plugin types with their param schemas."""
        from importlib.metadata import entry_points

        result = []
        for ep in entry_points(group="shenas.transformers"):
            try:
                cls = ep.load()
                inst = cls()
                schema = inst.param_schema() if hasattr(inst, "param_schema") else []
                result.append(
                    TransformerInfoType(
                        name=ep.name,
                        display_name=getattr(inst, "display_name", ep.name),
                        description=getattr(inst, "description", ""),
                        param_schema=[
                            ParamFieldType(
                                name=p["name"],
                                label=p.get("label", ""),
                                type=p.get("type", "text"),
                                required=p.get("required", False),
                                description=p.get("description", ""),
                                default=str(p["default"]) if p.get("default") is not None else None,
                                options=p.get("options"),
                                role=p.get("role"),
                            )
                            for p in schema
                        ],
                    )
                )
            except Exception:
                pass
        return sorted(result, key=lambda x: x.display_name)

    # -- Categories --

    @strawberry.field
    def category_sets(self) -> list[CategorySetType]:
        """Return all category sets with their values."""
        from app.categories import Category

        return [
            CategorySetType(
                id=c.id,
                display_name=c.display_name,
                description=c.description,
                values=[CategoryValueType(value=v.value, sort_order=v.sort_order, color=v.color) for v in c.values],
            )
            for c in Category.all(order_by="display_name")
        ]

    # -- Table introspection --

    @strawberry.field
    def table_columns(self, schema: str, table: str) -> list[str]:
        """Return column names for a DuckDB table."""
        from app.database import cursor

        with cursor() as cur:
            rows = cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                [schema, table],
            ).fetchall()
        return [r[0] for r in rows]

    @strawberry.field
    def table_metadata(self, schema: str, table: str) -> JSON:
        """Return full table metadata (columns, kind, time columns, plot hints)."""
        from app.database import cursor
        from app.plugin import Plugin

        meta = Plugin.find_table_metadata(schema, table)
        if meta:
            return meta  # ty: ignore[invalid-return-type]
        # Fallback: derive minimal metadata from DuckDB schema
        with cursor() as cur:
            rows = cur.execute(f'DESCRIBE "{schema}"."{table}"').fetchall()
        return {  # ty: ignore[invalid-return-type]
            "table": table,
            "schema": schema,
            "columns": [{"name": row[0], "db_type": row[1]} for row in rows],
        }

    @strawberry.field
    def preview_transform_sql(self, params: str, source_schema: str, source_table: str) -> str:
        """Generate SQL from structured SelectQuery params (for preview)."""
        import json

        from shenas_transformers.sql.query import SelectQuery

        data = json.loads(params)
        if "columns" not in data:
            return data.get("sql", "")
        query = SelectQuery.from_dict(data)
        source_qualified = f'"{source_schema}"."{source_table}"'
        sql, _ = query.to_sql(source_qualified)
        return sql

    @strawberry.field
    async def transforms(self, info: strawberry.types.Info, source: str | None = None) -> list[TransformType]:
        from shenas_transformers.core.transform import Transform

        rows = Transform.for_plugin(source) if source else Transform.all(order_by="id")
        resource_ids = list({ref for t in rows for ref in (t.source_ref.id, t.target_ref.id)})
        resources = await info.context["resource_loader"].load_many(resource_ids)
        resource_map = dict(zip(resource_ids, resources, strict=True))
        return [_transform_to_gql(t, resource_map=resource_map) for t in rows]

    @strawberry.field
    def transform(self, transform_id: int) -> TransformType | None:
        from shenas_transformers.core.transform import Transform

        t = Transform.find(transform_id)
        return _transform_to_gql(t) if t else None

    # -- Data Catalog --

    @strawberry.field
    async def data_resources(
        self,
        info: strawberry.types.Info,
        kind: str | None = None,
        plugin: str | None = None,
        tags: str | None = None,
        stale_only: bool = False,
    ) -> list[DataResourceType]:
        from app.data_catalog import catalog

        resources = catalog().list_resources(
            kind=kind, plugin=plugin, tags=tags, stale_only=stale_only, include_row_counts=False
        )
        counts = await info.context["row_count_loader"].load_many([r.id for r in resources])
        for r, count in zip(resources, counts, strict=True):
            r.actual_row_count = count
        return [_data_resource_to_gql(r) for r in resources]

    @strawberry.field
    def data_resource(self, resource_id: str) -> DataResourceType | None:
        from app.data_catalog import catalog

        r = catalog().get(resource_id)
        return _data_resource_to_gql(r) if r else None

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

        return {h.action_id: h.binding for h in Hotkey.all(order_by="action_id")}  # ty: ignore[invalid-return-type]

    @strawberry.field
    def workspace(self, info: strawberry.types.Info) -> JSON:  # noqa: ARG002
        import json

        from app.workspace import Workspace

        raw = Workspace.read_value("state")
        return json.loads(raw) if raw else {}  # ty: ignore[invalid-return-type]

    @strawberry.field
    def dashboards(self) -> list[DashboardType]:
        from app.plugin import PluginInstance
        from shenas_dashboards.core import Dashboard

        result = []
        for c in Dashboard.load_all(include_internal=False):
            inst = PluginInstance.find("dashboard", c.name)
            if inst is not None and not inst.enabled:
                continue
            result.append(
                DashboardType(
                    name=c.name,
                    display_name=c.display_name,
                    tag=c.tag,
                    js=f"/dashboards/{c.name}/{c.entrypoint}",
                    description=c.description,
                )
            )
        return result

    @strawberry.field
    def dependencies(self) -> list[DependencyEdge]:
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
        return [DependencyEdge(source=k, targets=v) for k, v in result.items()]

    # -- Models --

    @strawberry.field
    def models(self) -> list[ModelInfoType]:
        from shenas_models.core import Model

        result = []
        for cls in Model.load_all(include_internal=False):
            info = cls().get_info()
            result.append(
                ModelInfoType(
                    name=info.get("name", cls.name),
                    display_name=info.get("display_name", cls.name),
                    description=info.get("description", ""),
                    version=info.get("version", ""),
                    enabled=info.get("enabled", True),
                )
            )
        return sorted(result, key=lambda x: x.name)

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
    def catalog(self) -> list[DataResourceType]:
        """Return all queryable source / metric tables as DataResourceType.

        Equivalent to dataResources but without row counts for performance.
        Used by the LLM prompt builder.
        """
        from app.data_catalog import catalog

        return [_data_resource_to_gql(r) for r in catalog().list_resources(include_row_counts=False)]

    # -- Analysis modes --

    @strawberry.field
    def analysis_modes(self) -> JSON:
        """Return metadata for all registered analysis modes."""
        from shenas_analyses.core import Analysis
        from shenas_analyses.core.analytics.mode import list_modes

        Analysis.discover()
        return list_modes()  # ty: ignore[invalid-return-type]

    # -- Suggestions --
    #
    # Read-only listing of LLM-suggested datasets, transforms, and analyses.

    @strawberry.field
    def suggested_datasets(self, source: str | None = None) -> list[SuggestedDatasetType]:
        """Return suggested (not yet accepted) datasets, optionally filtered by source."""
        from app.plugin import PluginInstance

        suggestions = PluginInstance.suggested("dataset")
        if source:
            suggestions = [pi for pi in suggestions if source in ((pi.metadata or {}).get("source", ""))]
        return [
            SuggestedDatasetType(
                name=pi.name,
                is_suggested=bool(pi.is_suggested),
                enabled=bool(pi.enabled),
                table_name=(pi.metadata or {}).get("table_name"),
                grain=(pi.metadata or {}).get("grain"),
                title=(pi.metadata or {}).get("title"),
            )
            for pi in suggestions
        ]

    @strawberry.field
    def suggested_transforms(self, source: str | None = None) -> list[TransformType]:
        """Return all suggested (not yet accepted) transforms."""
        from shenas_transformers.core.transform import Transform

        return [_transform_to_gql(t) for t in Transform.suggested(source)]

    @strawberry.field
    def suggested_analyses(self) -> list[SuggestedAnalysisType]:
        """Return all suggested (not yet accepted) analysis hypotheses."""
        from app.hypotheses import Hypothesis

        return [
            SuggestedAnalysisType(
                id=h.id,
                question=h.question,
                rationale=h.plan or "",
                datasets_involved=(h.inputs or "").split(",") if h.inputs else [],  # ty: ignore[invalid-argument-type]
                complexity=h.mode or "",
            )
            for h in Hypothesis.suggested()
        ]

    # -- Hypotheses --
    #
    # Read-only listing + single fetch over the Hypothesis system table.
    # The mutations that create / run / promote hypotheses live in
    # app/graphql/mutations.py.

    @strawberry.field
    def hypotheses(self, limit: int | None = None) -> list[HypothesisType]:
        """Return every hypothesis row, most recent first."""
        from app.hypotheses import Hypothesis

        return [_hypothesis_to_gql(h) for h in Hypothesis.all(order_by="created_at DESC", limit=limit)]

    @strawberry.field
    def hypothesis(self, hypothesis_id: int) -> HypothesisType | None:
        """Return one hypothesis by id, or ``None`` if not found."""
        from app.hypotheses import Hypothesis

        h = Hypothesis.find(hypothesis_id)
        return _hypothesis_to_gql(h) if h else None

    # -- Entities --

    @strawberry.field
    def entity_types(self) -> list[EntityTypeType]:
        from app.entity import EntityType

        return [
            EntityTypeType(
                name=t.name,
                display_name=t.display_name,
                description=t.description,
                icon=t.icon,
                parent=t.parent,
                is_abstract=t.is_abstract,
                wikidata_qid=t.wikidata_qid,
            )
            for t in EntityType.all(order_by="name")
        ]

    @strawberry.field
    def entity_relationship_types(self) -> list[EntityRelationshipTypeType]:
        from app.entity import EntityRelationshipType, EntityType

        # Build parent -> children map to expand type constraints to include subtypes.
        all_types = EntityType.all()
        children_of: dict[str, set[str]] = {}
        for entity_type in all_types:
            if entity_type.parent:
                children_of.setdefault(entity_type.parent, set()).add(entity_type.name)

        def expand_with_subtypes(type_names: list[str]) -> list[str]:
            """Expand a list of type names to include all descendants."""
            result: set[str] = set()
            stack = list(type_names)
            while stack:
                current = stack.pop()
                if current not in result:
                    result.add(current)
                    stack.extend(children_of.get(current, ()))
            return sorted(result)

        return [
            EntityRelationshipTypeType(
                name=rel_type.name,
                display_name=rel_type.display_name,
                description=rel_type.description,
                inverse_name=rel_type.inverse_name,
                is_symmetric=rel_type.is_symmetric,
                domain_types=expand_with_subtypes(
                    [name.strip() for name in (rel_type.domain_types or "").split(",") if name.strip()]
                ),
                range_types=expand_with_subtypes(
                    [name.strip() for name in (rel_type.range_types or "").split(",") if name.strip()]
                ),
                wikidata_pid=getattr(rel_type, "wikidata_pid", None),
            )
            for rel_type in EntityRelationshipType.all(order_by="name")
        ]

    @strawberry.field
    def entities(self, info: strawberry.types.Info, status: str | None = None) -> list[GqlEntityType]:  # noqa: ARG002
        from app.entities.statements import Statement
        from app.entity import Entity

        # Find the "me" entity: the first human entity created at bootstrap.
        me_candidates = Entity.all(where="type = 'human'", order_by="id", limit=1)
        me_uuid = me_candidates[0].uuid if me_candidates else None
        where = f"status = '{status}'" if status else None

        # Batch-load sources for all entities in one query to avoid N+1.
        # One Statement.all() with a source filter replaces 1454 per-entity queries.
        sources_by_entity: dict[str, list[str]] = {}
        try:
            all_sourced = Statement.all(where="source IS NOT NULL AND source != ''")
            source_sets: dict[str, set[str]] = {}
            for stmt in all_sourced:
                source_sets.setdefault(stmt.entity_id, set()).add(stmt.source)
            sources_by_entity = {k: sorted(v) for k, v in source_sets.items()}
        except Exception:
            pass

        return [
            GqlEntityType.build(
                uuid=e.uuid,
                type=e.type,
                name=e.name,
                description=e.description,
                status=e.status,
                added_at=str(e.added_at) if e.added_at else None,
                updated_at=str(e.updated_at) if e.updated_at else None,
                is_me=(e.uuid == me_uuid),
                sources=sources_by_entity.get(e.uuid, []),
            )
            for e in Entity.all(where=where, order_by="name")
        ]

    @strawberry.field
    def source_entities_for_plugin(self, plugin: str) -> list[GqlEntityType]:
        """Entities related to a source plugin.

        Returns the union of:
        1. Entities this source produced (via ``statements.source``).
        2. Entities whose type matches the source's ``entity_types``
           declaration (so consumable entities like cities appear for
           OpenMeteo even before sync).
        """
        from app.database import cursor
        from app.entity import Entity, EntityType
        from app.plugin import Plugin

        me_candidates = Entity.all(where="type = 'human'", order_by="id", limit=1)
        me_uuid = me_candidates[0].uuid if me_candidates else None

        seen: set[str] = set()
        results: list[GqlEntityType] = []

        def _add(entity: Entity) -> None:
            if entity.uuid in seen:
                return
            seen.add(entity.uuid)
            results.append(
                GqlEntityType.build(
                    uuid=entity.uuid,
                    type=entity.type,
                    name=entity.name,
                    description=entity.description,
                    status=entity.status,
                    added_at=str(entity.added_at) if entity.added_at else None,
                    updated_at=str(entity.updated_at) if entity.updated_at else None,
                    is_me=(entity.uuid == me_uuid),
                )
            )

        # 1. Entities produced by this source (via statements).
        with cursor() as cur:
            has_scd2 = bool(
                cur.execute(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'entities' AND table_name = 'statements' AND column_name = '_dlt_valid_to'"
                ).fetchone()
            )
            scd2_filter = "AND s._dlt_valid_to IS NULL " if has_scd2 else ""
            rows = cur.execute(
                f"SELECT DISTINCT s.entity_id FROM entities.statements s WHERE s.source = ? {scd2_filter}",
                [plugin],
            ).fetchall()
        for (entity_id,) in rows:
            entity = Entity.find_by_uuid(entity_id)
            if entity:
                _add(entity)

        # 2. Entities whose type matches the source's entity_types.
        source_cls = Plugin.load_by_name_and_kind(plugin, "source")
        if source_cls:
            declared_types = getattr(source_cls, "entity_types", [])
            for type_name in declared_types:
                # Resolve concrete subtypes for abstract types.
                entity_type = EntityType.find(type_name)
                if entity_type and entity_type.is_abstract:
                    concrete = EntityType.all(where="is_abstract = FALSE")
                    for concrete_type in concrete:
                        if EntityType.is_subtype_of(concrete_type.name, type_name):
                            for entity in Entity.all(where="type = ?", params=[concrete_type.name], order_by="name"):
                                _add(entity)
                else:
                    for entity in Entity.all(where="type = ?", params=[type_name], order_by="name"):
                        _add(entity)

        results.sort(key=lambda entity: (entity.name or "").lower())
        return results

    @strawberry.field
    def properties(self, domain_type: str | None = None) -> list[PropertyType]:
        """List declared properties, optionally scoped to a single entity type.

        Returns global (``domain_type IS NULL``) properties alongside any
        type-specific ones, so the UI can render a single combined list when
        a domain is provided.
        """
        from app.entities.properties import Property

        if domain_type is not None:
            rows = Property.all(
                where="domain_type IS NULL OR domain_type = ?",
                params=[domain_type],
                order_by="label",
            )
        else:
            rows = Property.all(order_by="label")
        return [
            PropertyType(
                id=p.id,
                label=p.label,
                datatype=p.datatype or "string",
                domain_type=p.domain_type,
                source=p.source or "user",
                wikidata_pid=p.wikidata_pid,
                description=p.description,
            )
            for p in rows
        ]

    @strawberry.field
    def entity(self, info: strawberry.types.Info, uuid: str | None = None) -> GqlEntityType | None:  # noqa: ARG002
        from app.entity import Entity

        me_candidates = Entity.all(where="type = 'human'", order_by="id", limit=1)
        me_uuid = me_candidates[0].uuid if me_candidates else None
        if uuid is None:
            if me_uuid is None:
                return None
            uuid = me_uuid
        e = Entity.find_by_uuid(uuid)
        if e is None:
            return None
        return GqlEntityType.build(
            uuid=e.uuid,
            type=e.type,
            name=e.name,
            description=e.description,
            status=e.status,
            added_at=str(e.added_at) if e.added_at else None,
            updated_at=str(e.updated_at) if e.updated_at else None,
            is_me=(e.uuid == me_uuid),
        )

    @strawberry.field
    def entity_relationships(
        self,
        info: strawberry.types.Info,  # noqa: ARG002
        entity_uuid: str | None = None,
    ) -> list[GqlEntityRelationshipType]:
        from app.entity import EntityRelationship

        if entity_uuid is not None:
            rels = EntityRelationship.for_entity(entity_uuid)
        else:
            rels = EntityRelationship.all(order_by="from_uuid")
        return [
            GqlEntityRelationshipType(
                from_uuid=r.from_uuid,
                to_uuid=r.to_uuid,
                type=r.type,
                description=r.description,
                added_at=str(r.added_at) if r.added_at else None,
                updated_at=str(r.updated_at) if r.updated_at else None,
            )
            for r in rels
        ]


def _hypothesis_to_gql(h: Any) -> HypothesisType:
    return HypothesisType(
        id=h.id,
        question=h.question,
        plan=h.plan,
        recipe_json=h.recipe_json or "",
        inputs=h.inputs,
        result_json=h.result_json,
        interpretation=h.interpretation,
        created_at=str(h.created_at) if h.created_at else None,
        model=h.model,
        promoted_to=h.promoted_to,
        llm_input_tokens=h.llm_input_tokens,
        llm_output_tokens=h.llm_output_tokens,
        llm_elapsed_ms=h.llm_elapsed_ms,
        query_elapsed_ms=h.query_elapsed_ms,
        wall_clock_ms=h.wall_clock_ms,
        mode=h.mode,
        parent_id=getattr(h, "parent_id", None),
        is_suggested=getattr(h, "is_suggested", None),
    )
