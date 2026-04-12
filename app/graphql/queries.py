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
    DashboardType,
    DataResourceType,
    DBStatusType,
    DependencyEdge,
    FindingType,
    FreshnessInfoType,
    HypothesisSuggestionType,
    HypothesisType,
    ModelInfoType,
    ParamFieldType,
    PluginInfoType,
    QualityCheckType,
    QualityInfoType,
    ScheduleInfoType,
    SuggestedAnalysisType,
    SuggestedDatasetType,
    TableEntry,
    ThemeInfo,
    TimeColumnsInfoType,
    TransformerInfoType,
    TransformType,
)

if TYPE_CHECKING:
    from shenas_transformers.core.transform import Transform

    from app.data_catalog import DataResource
    from shenas_plugins.core.plugin import Plugin


def _plugin_to_gql(plugin: Plugin) -> PluginInfoType:
    from app.models import PluginInfo

    return PluginInfoType.from_pydantic(  # ty: ignore[unresolved-attribute]
        PluginInfo(
            name=plugin.name,
            display_name=getattr(plugin, "display_name", plugin.name),
            description=getattr(plugin, "description", ""),
        ),
    )


def _data_resource_to_gql(r: DataResource) -> DataResourceType:
    return DataResourceType(
        id=r.id,
        schema_name=r.ref.schema,
        table_name=r.ref.table,
        display_name=r.display_name,
        description=r.effective_description,
        plugin=_plugin_to_gql(r.plugin),
        kind=r.kind,
        query_hint=r.query_hint,
        as_of_macro=r.as_of_macro,
        primary_key=r.primary_key,
        columns=[
            ColumnInfoType(
                name=c.name,
                db_type=c.db_type,
                nullable=c.nullable,
                description=c.description,
                unit=c.unit,
                value_range=list(c.value_range) if c.value_range else None,
                example_value=c.example_value,
                interpretation=c.interpretation,
            )
            for c in r.columns
        ],
        time_columns=TimeColumnsInfoType(
            time_at=r.time_columns.time_at,
            time_start=r.time_columns.time_start,
            time_end=r.time_columns.time_end,
            cursor_column=r.time_columns.cursor_column,
            observed_at_injected=r.time_columns.observed_at_injected,
        ),
        freshness=FreshnessInfoType(
            last_refreshed=r.last_refreshed,
            sla_minutes=r.freshness_sla_minutes,
            is_stale=r.is_stale,
        ),
        quality=QualityInfoType(
            expected_row_count_min=r.expected_row_count_min,
            expected_row_count_max=r.expected_row_count_max,
            actual_row_count=r.actual_row_count,
            latest_checks=[
                QualityCheckType(
                    check_type=c.check_type,
                    status=c.status,
                    message=c.message,
                    value=c.value,
                    checked_at=c.checked_at,
                )
                for c in r.quality_checks
            ],
        ),
        user_notes=r.user_notes,
        tags=r.tags,
        upstream_transforms=[_transform_to_gql(t) for t in r.upstream_transforms]
        if r.upstream_transforms is not None
        else None,
        downstream_transforms=[_transform_to_gql(t) for t in r.downstream_transforms]
        if r.downstream_transforms is not None
        else None,
    )


def _transform_to_gql(t: Transform) -> TransformType:
    from app.data_catalog import catalog

    return TransformType(
        id=t.id,
        transform_type=t.transform_type,
        source=_data_resource_to_gql(catalog().get_resource(t.source_ref.id)),
        target=_data_resource_to_gql(catalog().get_resource(t.target_ref.id)),
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
    def auth_fields(self, pipe: str) -> AuthFieldsType:
        from app.api.auth import auth_fields

        result = auth_fields(pipe)
        return AuthFieldsType.from_pydantic(result)  # ty: ignore[unresolved-attribute]

    # -- Config --

    @strawberry.field
    def config_value(self, kind: str, name: str, key: str) -> str | None:
        from shenas_plugins.core.plugin import Plugin

        try:
            cls = Plugin.load_by_name_and_kind(name, kind)
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
        from shenas_plugins.core.plugin import VALID_KINDS, Plugin

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
        from shenas_plugins.core.plugin import Plugin

        cls = Plugin.load_by_name_and_kind(name, kind) or Plugin._load_fresh(kind, name)
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
        from app.models import ScheduleInfo
        from shenas_sources.core.source import Source

        result = []
        for cls in Source.load_all(include_internal=False):
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

    @strawberry.field
    def category_set(self, set_id: str) -> CategorySetType | None:
        """Return a single category set with values."""
        from app.categories import Category

        c = Category.find(set_id)
        if not c:
            return None
        return CategorySetType(
            id=c.id,
            display_name=c.display_name,
            description=c.description,
            values=[CategoryValueType(value=v.value, sort_order=v.sort_order, color=v.color) for v in c.values],
        )

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
    def transforms(self, source: str | None = None) -> list[TransformType]:
        from shenas_transformers.core.transform import Transform

        rows = Transform.for_plugin(source) if source else Transform.all(order_by="id")
        return [_transform_to_gql(t) for t in rows]

    @strawberry.field
    def transform(self, transform_id: int) -> TransformType | None:
        from shenas_transformers.core.transform import Transform

        t = Transform.find(transform_id)
        return _transform_to_gql(t) if t else None

    # -- Data Catalog --

    @strawberry.field
    def data_resources(
        self,
        kind: str | None = None,
        plugin: str | None = None,
        tags: str | None = None,
        stale_only: bool = False,
    ) -> list[DataResourceType]:
        from app.data_catalog import catalog

        resources = catalog().list_resources(kind=kind, plugin=plugin, tags=tags, stale_only=stale_only)
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

        return Hotkey.get_all()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def workspace(self, info: strawberry.types.Info) -> JSON:  # noqa: ARG002
        from app.workspace import Workspace

        return Workspace.get()  # ty: ignore[invalid-return-type]

    @strawberry.field
    def dashboards(self) -> list[DashboardType]:
        from shenas_dashboards.core import Dashboard
        from shenas_plugins.core.plugin import PluginInstance

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

    @strawberry.field
    def model_status(self, name: str) -> JSON:
        from shenas_models.core import Model

        cls = Model.load_by_name(name)
        if not cls:
            return {"name": name, "available": False, "round": None}  # ty: ignore[invalid-return-type]
        return cls().training_status  # ty: ignore[invalid-return-type]

    @strawberry.field
    def model_predict(self, name: str) -> JSON:
        from shenas_models.core import Model

        cls = Model.load_by_name(name)
        if not cls:
            return None  # ty: ignore[invalid-return-type]
        return cls().predict()  # ty: ignore[invalid-return-type]

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

        from shenas_plugins.core.analytics.mode import list_modes

        Analysis.discover()
        return list_modes()  # ty: ignore[invalid-return-type]

    # -- Literature --

    @strawberry.field
    def literature_findings(self, limit: int | None = None) -> list[FindingType]:
        """Return stored literature findings."""
        from app.literature import Finding

        rows = Finding.all(order_by="id DESC", limit=limit)
        return [_finding_to_gql(f) for f in rows]

    @strawberry.field
    def suggested_hypotheses(self, limit: int = 10) -> list[HypothesisSuggestionType]:
        """Return proactive hypothesis suggestions from literature cross-referenced with installed data."""
        from app.data_catalog import catalog as get_catalog
        from app.literature import suggest_hypotheses

        catalog = get_catalog().metadata_by_id()
        suggestions = suggest_hypotheses(catalog, limit=limit)
        return [
            HypothesisSuggestionType(
                question=s.question,
                rationale=s.rationale,
                datasets_involved=s.datasets_involved,
                complexity=getattr(s, "complexity", ""),
                score=getattr(s, "score", 0.0),
            )
            for s in suggestions
        ]

    # -- Hypotheses --
    #
    # Read-only listing + single fetch over the Hypothesis system table.
    # The mutations that create / run / promote hypotheses live in
    # app/graphql/mutations.py.

    # -- Suggestions --
    #
    # Read-only listing of LLM-suggested datasets, transforms, and analyses.

    @strawberry.field
    def suggested_datasets(self) -> list[SuggestedDatasetType]:
        """Return all suggested (not yet accepted) datasets."""
        from shenas_plugins.core.plugin import PluginInstance

        return [
            SuggestedDatasetType(
                name=pi.name,
                is_suggested=bool(pi.is_suggested),
                enabled=bool(pi.enabled),
                table_name=(pi.metadata or {}).get("table_name"),
                grain=(pi.metadata or {}).get("grain"),
                title=(pi.metadata or {}).get("title"),
            )
            for pi in PluginInstance.suggested("dataset")
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


def _finding_to_gql(f: Any) -> FindingType:
    return FindingType(
        id=f.id,
        exposure=f.exposure,
        outcome=f.outcome,
        direction=f.direction or "",
        effect_size=f.effect_size,
        ci_low=f.ci_low,
        ci_high=f.ci_high,
        evidence_level=f.evidence_level,
        sample_size=f.sample_size,
        mechanism=f.mechanism,
        citation=f.citation or "",
        doi=f.doi,
        exposure_categories=f.exposure_categories,
        outcome_categories=f.outcome_categories,
        source_ref=f.source_ref,
    )


def _safe_json_load(s: str) -> Any:
    import json

    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None
