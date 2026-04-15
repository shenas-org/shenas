"""GraphQL Mutation resolvers."""

from __future__ import annotations

import json

import strawberry
from strawberry.scalars import JSON  # noqa: TC002 - needed at runtime by Strawberry

from app.categories import Category
from app.graphql.queries import _data_resource_to_gql, _transform_to_gql
from app.graphql.types import (
    AuthResponseType,
    CategorySetType,
    CategoryValueType,
    DataResourceAnnotationInput,
    DataResourceType,
    EntityCreateInput,
    EntityUpdateInput,
    GqlEntityRelationshipType,
    GqlEntityType,
    InstallResponseType,
    OkType,
    QualityCheckType,
    RemoveResponseType,
    SeedResultType,
    TransformCreateInput,
    TransformRunResultType,
    TransformType,
)


def _source_entry_point_names() -> list[str]:
    """Return names of all installed source plugins."""
    from importlib.metadata import entry_points

    return [ep.name for ep in entry_points(group="shenas.sources")]


def _category_to_gql(c: Category) -> CategorySetType:
    return CategorySetType(
        id=c.id,
        display_name=c.display_name,
        description=c.description,
        values=[CategoryValueType(value=v.value, sort_order=v.sort_order, color=v.color) for v in c.values],
    )


def _build_catalog() -> dict[str, dict]:
    """Return ``{qualified_table: table_metadata}`` for the recipe runner."""
    from app.data_catalog import catalog

    return catalog().metadata_by_id()


@strawberry.type
class Mutation:
    # -- Auth --

    @strawberry.mutation
    def authenticate(
        self,
        info: strawberry.types.Info,
        pipe: str,
        credentials: JSON,
        callback_url: str | None = None,
    ) -> AuthResponseType:
        from app.models import AuthResponse
        from shenas_sources.core.source import Source

        cls = Source.load_by_name(pipe)
        if not cls:
            return AuthResponseType.from_pydantic(AuthResponse(ok=False, error=f"Source not found: {pipe}"))  # ty: ignore[unresolved-attribute]
        source = cls()
        # Build callback URL for OAuth redirect flow
        redirect_uri = None
        if source.supports_oauth_redirect:
            if callback_url:
                redirect_uri = callback_url
            else:
                request = info.context.get("request")
                if request:
                    base = str(request.base_url).rstrip("/")
                    redirect_uri = f"{base}/api/auth/source/{pipe}/callback"
        result = source.handle_auth(credentials, redirect_uri=redirect_uri)  # ty: ignore[invalid-argument-type]
        return AuthResponseType.from_pydantic(AuthResponse(**result))  # ty: ignore[unresolved-attribute]

    # -- Config --

    @strawberry.mutation
    def set_config(self, kind: str, name: str, key: str, value: str) -> OkType:
        from app.models import OkResponse
        from app.plugin import Plugin

        cls = Plugin.load_by_name_and_kind(name, kind)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))  # ty: ignore[unresolved-attribute]
        plugin = cls()
        plugin.set_config_value(key, value)
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def delete_config(self, kind: str, name: str) -> OkType:
        from app.models import OkResponse
        from app.plugin import Plugin

        cls = Plugin.load_by_name_and_kind(name, kind)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))  # ty: ignore[unresolved-attribute]
        cls().delete_config()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def delete_config_key(self, kind: str, name: str, key: str) -> OkType:
        from app.models import OkResponse
        from app.plugin import Plugin

        cls = Plugin.load_by_name_and_kind(name, kind)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))  # ty: ignore[unresolved-attribute]
        cls().set_config_value(key, None)
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    # -- Database --

    @strawberry.mutation
    def generate_db_key(self) -> OkType:
        from app.database import generate_db_key, set_db_key
        from app.models import OkResponse

        key = generate_db_key()
        set_db_key(key)
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def flush_schema(self, schema_plugin: str) -> JSON:
        from app.api.db import flush_schema

        return flush_schema(schema_plugin)  # ty: ignore[invalid-return-type]

    # -- Plugins --

    @strawberry.mutation
    def install_plugins(
        self,
        kind: str,
        names: list[str],
        index_url: str | None = None,
        skip_verify: bool = False,
    ) -> InstallResponseType:
        from app.models import InstallResponse, InstallResult
        from app.plugin import DEFAULT_INDEX, Plugin

        results = []
        for n in names:
            ok, message = Plugin.install(kind, n, index_url=index_url or DEFAULT_INDEX, skip_verify=skip_verify)
            results.append(InstallResult(name=n, ok=ok, message=message))
        return InstallResponseType.from_pydantic(InstallResponse(results=results))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def remove_plugin(self, kind: str, name: str) -> RemoveResponseType:
        from app.models import RemoveResponse
        from app.plugin import Plugin

        ok, message = Plugin.uninstall(kind, name)
        return RemoveResponseType.from_pydantic(RemoveResponse(ok=ok, message=message))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def enable_plugin(self, kind: str, name: str) -> OkType:
        from app.models import OkResponse
        from app.plugin import PluginInstance

        inst = PluginInstance.get_or_create(kind, name)
        msg = inst.enable()
        return OkType.from_pydantic(OkResponse(ok=True, message=msg))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def disable_plugin(self, kind: str, name: str) -> OkType:
        from app.models import OkResponse
        from app.plugin import PluginInstance

        inst = PluginInstance.find(kind, name)
        if not inst:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not tracked: {kind}/{name}"))  # ty: ignore[unresolved-attribute]
        try:
            msg = inst.disable()
        except ValueError as exc:
            return OkType.from_pydantic(OkResponse(ok=False, message=str(exc)))  # ty: ignore[unresolved-attribute]
        return OkType.from_pydantic(OkResponse(ok=True, message=msg))  # ty: ignore[unresolved-attribute]

    # -- Data Catalog --

    @strawberry.mutation
    def update_data_resource(self, resource_id: str, annotation: DataResourceAnnotationInput) -> DataResourceType | None:
        from app.data_catalog import catalog

        fields: dict = {}
        if annotation.user_notes is not None:
            fields["user_notes"] = annotation.user_notes
        if annotation.tags is not None:
            fields["tags"] = annotation.tags
        if annotation.description is not None:
            fields["description_override"] = annotation.description
        if annotation.freshness_sla_minutes is not None:
            fields["freshness_sla_minutes"] = annotation.freshness_sla_minutes
        if annotation.expected_row_count_min is not None:
            fields["expected_row_count_min"] = annotation.expected_row_count_min
        if annotation.expected_row_count_max is not None:
            fields["expected_row_count_max"] = annotation.expected_row_count_max
        r = catalog().annotate(resource_id, **fields)
        return _data_resource_to_gql(r) if r else None

    @strawberry.mutation
    def run_quality_checks(self, resource_id: str | None = None) -> list[QualityCheckType]:
        from app.data_catalog import catalog

        checks = catalog().run_quality_checks(resource_id)
        return [
            QualityCheckType(
                check_type=c.check_type,
                status=c.status,
                message=c.message,
                value=c.value,
                checked_at=c.checked_at,
            )
            for c in checks
        ]

    # -- Categories --

    @strawberry.mutation
    def create_category_set(self, set_id: str, display_name: str, description: str = "") -> CategorySetType:
        c = Category(id=set_id, display_name=display_name, description=description)
        c.insert()
        return _category_to_gql(c)

    @strawberry.mutation
    def update_category_set(
        self, set_id: str, display_name: str | None = None, description: str | None = None
    ) -> CategorySetType | None:
        c = Category.find(set_id)
        if not c:
            return None
        if display_name is not None:
            c.display_name = display_name
        if description is not None:
            c.description = description
        c.save()
        return _category_to_gql(c)

    @strawberry.mutation
    def delete_category_set(self, set_id: str) -> OkType:
        from app.models import OkResponse

        c = Category.find(set_id)
        if c:
            c.delete()
        return OkType.from_pydantic(OkResponse(ok=c is not None))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def update_category_values(self, set_id: str, values: str) -> CategorySetType | None:
        """Replace all values in a set. values is a JSON array of {value, sortOrder?, color?}."""
        import json

        c = Category.find(set_id)
        if not c:
            return None
        c.replace_values(json.loads(values))
        return _category_to_gql(c)

    # -- Transforms --

    @strawberry.mutation
    def create_transform(self, transform_input: TransformCreateInput) -> TransformType:
        from shenas_transformers.core.transform import Transform

        t = Transform.create(
            transform_type=transform_input.transform_type,
            source_data_resource_id=f"{transform_input.source_duckdb_schema}.{transform_input.source_duckdb_table}",
            target_data_resource_id=f"{transform_input.target_duckdb_schema}.{transform_input.target_duckdb_table}",
            source_plugin=transform_input.source_plugin,
            params=transform_input.params,
            description=transform_input.description,
        )
        return _transform_to_gql(t)

    @strawberry.mutation
    def update_transform(self, transform_id: int, params: str) -> TransformType | None:
        from shenas_transformers.core.transform import Transform

        existing = Transform.find(transform_id)
        if not existing:
            return None
        t = existing.update_params(params)
        return _transform_to_gql(t) if t else None

    @strawberry.mutation
    def delete_transform(self, transform_id: int) -> OkType:
        from shenas_transformers.core.transform import Transform

        from app.models import OkResponse

        t = Transform.find(transform_id)
        if t:
            t.delete()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def enable_transform(self, transform_id: int) -> TransformType | None:
        from shenas_transformers.core.transform import Transform

        t = Transform.find(transform_id)
        if not t:
            return None
        updated = t.set_enabled(True)
        return _transform_to_gql(updated) if updated else None

    @strawberry.mutation
    def disable_transform(self, transform_id: int) -> TransformType | None:
        from shenas_transformers.core.transform import Transform

        t = Transform.find(transform_id)
        if not t:
            return None
        updated = t.set_enabled(False)
        return _transform_to_gql(updated) if updated else None

    @strawberry.mutation
    def test_transform(self, transform_id: int, limit: int = 10) -> JSON:
        from shenas_transformers.core.transform import Transform

        t = Transform.find(transform_id)
        return t.test(limit) if t else []  # ty: ignore[invalid-return-type]

    @strawberry.mutation
    def seed_transforms(self) -> SeedResultType:
        from shenas_transformers.core import Transformer

        seeded: list[str] = []
        plugins = Transformer.load_all()
        for ep_name in _source_entry_point_names():
            for cls in plugins:
                plugin = cls()
                inst = plugin.instance()
                if not inst or inst.enabled:
                    plugin.seed_defaults_for_source(ep_name)
            seeded.append(ep_name)
        return SeedResultType(seeded=seeded, count=len(seeded))

    @strawberry.mutation
    def run_pipe_transforms(self, pipe: str) -> TransformRunResultType:
        from shenas_transformers.core.transform import Transform

        from app.database import connect

        count = Transform.run_for_source(connect(), pipe)
        return TransformRunResultType(name=pipe, count=count)

    @strawberry.mutation
    def run_schema_transforms(self, schema: str) -> TransformRunResultType:
        from shenas_transformers.core.transform import Transform

        from app.database import connect

        count = Transform.run_for_target(connect(), schema)
        return TransformRunResultType(name=schema, count=count)

    # -- Hotkeys --

    @strawberry.mutation
    def set_hotkey(self, action_id: str, binding: str, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        Hotkey(action_id=action_id).set_binding(binding)
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def delete_hotkey(self, action_id: str, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        Hotkey(action_id=action_id).delete()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def reset_hotkeys(self, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        Hotkey.reset()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    # -- Workspace --

    @strawberry.mutation
    def save_workspace(self, data: JSON, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        import json

        from app.models import OkResponse
        from app.workspace import Workspace

        Workspace.write_row(state=json.dumps(data))
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    # -- Hypotheses --
    #
    # CRUD-shaped mutations over the Hypothesis system table. The recipe
    # is supplied as a JSON DAG (the same format Hypothesis._serialize_recipe
    # produces) so this layer is LLM-agnostic -- a curl request or test
    # can drive it directly. askHypothesis (the LLM-driven mutation)
    # lands on top of these.

    @strawberry.mutation
    def create_hypothesis(self, question: str, plan: str = "", model: str = "", mode: str = "hypothesis") -> JSON:
        """Create an empty hypothesis row from a question. No recipe yet."""
        from shenas_analyses.core.analytics import Recipe

        from app.hypotheses import Hypothesis

        empty = Recipe(nodes={}, final="")
        h = Hypothesis.create(question, empty, plan=plan, model=model, mode=mode)
        return {"id": h.id, "question": h.question, "mode": h.mode}  # ty: ignore[invalid-return-type]

    @strawberry.mutation
    def run_recipe(self, hypothesis_id: int, recipe_json: str) -> JSON:
        """Attach a recipe DAG (JSON) to a hypothesis, run it, persist the result.

        ``recipe_json`` is the same shape Hypothesis._serialize_recipe
        emits: ``{"nodes": {name: {type, ...}}, "final": str}``.
        """
        import json

        from shenas_analyses.core.analytics import (
            ErrorResult,
            OpCall,
            Recipe,
            SourceRef,
            run_recipe,
        )

        from app.database import analytics_backend
        from app.hypotheses import Hypothesis, _extract_input_tables, _serialize_recipe

        h = Hypothesis.find(hypothesis_id)
        if h is None:
            return {"error": f"hypothesis {hypothesis_id} not found"}  # ty: ignore[invalid-return-type]

        payload = json.loads(recipe_json)
        nodes: dict[str, SourceRef | OpCall] = {}
        for name, node in payload.get("nodes", {}).items():
            if node.get("type") == "source":
                nodes[name] = SourceRef(table=node["table"])
            else:
                nodes[name] = OpCall(
                    op_name=node["op_name"],
                    params=node.get("params", {}),
                    inputs=tuple(node.get("inputs", ())),
                )
        recipe = Recipe(nodes=nodes, final=payload.get("final", ""))

        # Persist the new recipe + inputs *before* running so even a runner
        # crash leaves a recoverable record of what was attempted.
        h.recipe_json = _serialize_recipe(recipe)
        h.inputs = ",".join(sorted(_extract_input_tables(recipe)))
        h.save()

        catalog = _build_catalog()

        # Cache lookup: hash recipe + freshness of inputs.
        from app.recipe_cache import RecipeCache

        cache_key = RecipeCache.key_for(h.recipe_json, _extract_input_tables(recipe))
        cached_row = RecipeCache.find(cache_key)
        if cached_row is not None and cached_row.payload is not None:
            cached = cached_row.payload
            h.result_json = json.dumps(cached)
            h.save()
            return {"id": h.id, "result": cached, "ok": cached.get("type") != "error", "cached": True}  # ty: ignore[invalid-return-type]

        result = run_recipe(recipe, catalog, backend=analytics_backend())
        h.attach_result(result)
        if not isinstance(result, ErrorResult):
            RecipeCache.put(cache_key, result.model_dump())
        return {  # ty: ignore[invalid-return-type]
            "id": h.id,
            "result": result.model_dump(),
            "ok": not isinstance(result, ErrorResult),
            "cached": False,
        }

    # -- Forking --

    @strawberry.mutation
    def fork_hypothesis(self, hypothesis_id: int) -> JSON:
        """Create a new hypothesis that copies the parent's question + recipe.

        The fork has its own id, its own result history, and its own
        cost / latency tracking. Use this to try a different recipe
        against the same question without losing the original.
        """
        from app.hypotheses import Hypothesis

        parent = Hypothesis.find(hypothesis_id)
        if parent is None:
            return {"error": f"hypothesis {hypothesis_id} not found"}  # ty: ignore[invalid-return-type]

        fork = Hypothesis(
            question=parent.question,
            plan=parent.plan or "",
            recipe_json=parent.recipe_json or "",
            inputs=parent.inputs or "",
            model=parent.model or "",
            mode=parent.mode or "hypothesis",
            parent_id=parent.id,
        )
        fork.insert()
        return {"id": fork.id, "parent_id": parent.id, "question": fork.question}  # ty: ignore[invalid-return-type]

    # -- Promotion --

    @strawberry.mutation
    def promote_hypothesis(self, hypothesis_id: int, name: str, metric_schema: str = "metrics") -> JSON:
        """Promote a hypothesis into a canonical MetricTable.

        Inserts a row into ``shenas_system.promoted_metrics``. The
        promoted thing is then visible to the catalog walker as a
        synthesized ``MetricTable`` subclass; no Python source files
        are generated.
        """
        from app.hypotheses import Hypothesis
        from app.promotion import promote_hypothesis as _promote

        h = Hypothesis.find(hypothesis_id)
        if h is None:
            return {"error": f"hypothesis {hypothesis_id} not found"}  # ty: ignore[invalid-return-type]
        try:
            record = _promote(h, name=name, metric_schema=metric_schema)
        except ValueError as exc:
            return {"error": str(exc)}  # ty: ignore[invalid-return-type]
        return {  # ty: ignore[invalid-return-type]
            "id": h.id,
            "promoted_to": h.promoted_to,
            "qualified": record.qualified,
        }

    # -- LLM-driven hypothesis --

    @strawberry.mutation
    def ask_hypothesis(self, question: str, mode: str = "hypothesis") -> JSON:  # noqa: PLR0915 -- linear narrative is clearer than splitting
        """End-to-end: create a hypothesis, ask the LLM for a recipe, run it, persist.

        The LLM provider is constructed via ``get_llm_provider()`` which
        uses the shenas.net proxy. The ``mode`` parameter selects which
        analysis strategy the LLM uses (operation vocabulary, system
        prompt framing). Returns the hypothesis id, the LLM's plan,
        the recipe payload, the run result, and a per-turn cost block
        (input/output tokens, llm/query/wall_clock elapsed ms).
        """
        import time

        from shenas_analyses.core import Analysis
        from shenas_analyses.core.analytics import (
            ErrorResult,
            OpCall,
            Recipe,
            SourceRef,
            ask_for_recipe_with_retry,
            run_recipe,
        )
        from shenas_analyses.core.analytics.mode import get_mode

        from app.database import analytics_backend
        from app.hypotheses import Hypothesis, _extract_input_tables, _serialize_recipe
        from app.llm import get_llm_provider

        Analysis.discover()
        try:
            analysis_mode = get_mode(mode)
        except KeyError as exc:
            return {"ok": False, "error": {"message": str(exc)}}  # ty: ignore[invalid-return-type]

        provider = get_llm_provider()
        wall_start = time.monotonic()

        # Step 1: create empty hypothesis row so we can persist failures.
        empty = Recipe(nodes={}, final="")
        h = Hypothesis.create(question, empty, model=provider.name, mode=mode)

        # Step 2: ask the LLM for a recipe with one validation retry.
        def _validate_payload(p: dict) -> None:
            tmp_nodes: dict = {}
            for nm, nd in p.get("nodes", {}).items():
                if nd.get("type") == "source":
                    tmp_nodes[nm] = SourceRef(table=nd["table"])
                else:
                    tmp_nodes[nm] = OpCall(
                        op_name=nd.get("op_name", ""),
                        params=nd.get("params", {}),
                        inputs=tuple(nd.get("inputs", ())),
                    )
            Recipe(nodes=tmp_nodes, final=p.get("final", "")).validate()  # ty: ignore[missing-argument]

        catalog = _build_catalog()
        llm_start = time.monotonic()
        try:
            payload, retry_errors = ask_for_recipe_with_retry(
                provider,
                question,
                catalog,
                mode=analysis_mode,
                validate=_validate_payload,
                max_attempts=2,
            )
            if retry_errors and not payload.get("nodes"):
                msg = f"validation failed after retries: {retry_errors[-1]}"
                raise RuntimeError(msg)  # noqa: TRY301 -- inner func indirection isn't worth it here
        except Exception as exc:
            llm_elapsed_ms = (time.monotonic() - llm_start) * 1000.0
            err = {
                "type": "error",
                "message": f"LLM call failed: {exc}",
                "kind": "validation",
                "elapsed_ms": 0.0,
                "sql": "",
            }
            h.result_json = json.dumps(err)
            h.llm_input_tokens = getattr(provider, "last_input_tokens", 0)
            h.llm_output_tokens = getattr(provider, "last_output_tokens", 0)
            h.llm_elapsed_ms = llm_elapsed_ms
            h.wall_clock_ms = (time.monotonic() - wall_start) * 1000.0
            h.save()
            return {"id": h.id, "ok": False, "error": err}  # ty: ignore[invalid-return-type]
        llm_elapsed_ms = (time.monotonic() - llm_start) * 1000.0

        plan = payload.get("plan", "")
        nodes_payload = payload.get("nodes", {})
        nodes: dict[str, SourceRef | OpCall] = {}
        for name, node in nodes_payload.items():
            if node.get("type") == "source":
                nodes[name] = SourceRef(table=node["table"])
            else:
                nodes[name] = OpCall(
                    op_name=node.get("op_name", ""),
                    params=node.get("params", {}),
                    inputs=tuple(node.get("inputs", ())),
                )
        recipe = Recipe(nodes=nodes, final=payload.get("final", ""))

        # Step 3: persist the recipe + plan before running.
        h.plan = plan
        h.recipe_json = _serialize_recipe(recipe)
        h.inputs = ",".join(sorted(_extract_input_tables(recipe)))
        h.save()

        # Step 4: run.
        query_start = time.monotonic()
        result = run_recipe(recipe, catalog, backend=analytics_backend())
        query_elapsed_ms = (time.monotonic() - query_start) * 1000.0
        h.attach_result(result)
        # Step 5: persist cost / latency.
        h.llm_input_tokens = getattr(provider, "last_input_tokens", 0)
        h.llm_output_tokens = getattr(provider, "last_output_tokens", 0)
        h.llm_elapsed_ms = llm_elapsed_ms
        h.query_elapsed_ms = query_elapsed_ms
        h.wall_clock_ms = (time.monotonic() - wall_start) * 1000.0
        h.save()
        return {  # ty: ignore[invalid-return-type]
            "id": h.id,
            "plan": plan,
            "mode": mode,
            "recipe": payload,
            "result": result.model_dump(),
            "ok": not isinstance(result, ErrorResult),
            "cost": {
                "llm_input_tokens": h.llm_input_tokens,
                "llm_output_tokens": h.llm_output_tokens,
                "llm_elapsed_ms": h.llm_elapsed_ms,
                "query_elapsed_ms": h.query_elapsed_ms,
                "wall_clock_ms": h.wall_clock_ms,
            },
        }

    # -- Literature --

    @strawberry.mutation
    def refresh_literature(self, papers_per_pair: int = 5, min_citations: int = 50) -> JSON:
        """Fetch papers and extract structured findings via the API gateway."""
        from app.data_catalog import catalog as get_catalog
        from app.literature_fetch import refresh_findings

        catalog = get_catalog().metadata_by_id()
        return refresh_findings(catalog, papers_per_pair=papers_per_pair, min_citations=min_citations)  # ty: ignore[invalid-return-type]

    # -- LLM Suggestions --
    #
    # Two suggestion flows: dataset+transform suggestions (given sources)
    # and analysis suggestions (given datasets). Each persists suggestions
    # into the domain model with is_suggested=True and returns them for
    # user review.

    @strawberry.mutation
    def suggest_datasets(self, source: str | None = None) -> JSON:
        """Ask LLM to suggest canonical metric tables + transforms for installed sources."""
        import json
        import time
        import uuid

        from shenas_transformers.core.transform import Transform

        from app.data_catalog import _walk_metrics, _walk_sources
        from app.llm import get_llm_provider
        from app.plugin import PluginInstance
        from shenas_datasets.core.suggest import ask_for_dataset_suggestions, validate_dataset_payload

        provider = get_llm_provider()
        wall_start = time.monotonic()

        # Build catalogs
        source_catalog = [meta for meta, _plugin in _walk_sources()]
        if source:
            source_catalog = [t for t in source_catalog if t.get("schema") == source]
        existing_metrics = [meta for meta, _plugin in _walk_metrics()]

        if not source_catalog:
            return {"ok": False, "error": "No source tables found", "suggestions": []}  # ty: ignore[invalid-return-type]

        # Ask LLM
        try:
            payload = ask_for_dataset_suggestions(provider, source_catalog, existing_metrics)
            validate_dataset_payload(payload)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "suggestions": []}  # ty: ignore[invalid-return-type]

        # Persist suggestions
        batch_id = str(uuid.uuid4())[:8]
        suggestions = payload.get("suggestions", [])
        created: list[dict] = []
        source_context = source or ",".join(sorted({t.get("schema", "") for t in source_catalog}))

        for s in suggestions:
            metadata = {
                "table_name": s["table_name"],
                "grain": s["grain"],
                "columns": s["columns"],
                "primary_key": s["primary_key"],
                "transforms": s.get("transforms", []),
                "description": s.get("description", ""),
                "source": source_context,
            }
            pi = PluginInstance(
                kind="dataset",
                name=s["table_name"],
                enabled=False,
                is_suggested=True,
                metadata_json=json.dumps(metadata),
            )
            pi.insert()

            # Also create suggested transform instances
            for t in s.get("transforms", []):
                Transform.create_suggested(
                    source_data_resource_id=f"{t['source_schema']}.{t['source_table']}",
                    target_data_resource_id=f"metrics.{s['table_name']}",
                    source_plugin=t["source_plugin"],
                    params=json.dumps({"sql": t["sql"]}),
                    description=t.get("description", ""),
                )

            created.append(
                {
                    "name": s["table_name"],
                    "title": s.get("title", ""),
                    "description": s.get("description", ""),
                    "grain": s["grain"],
                    "column_count": len(s["columns"]),
                    "transform_count": len(s.get("transforms", [])),
                }
            )

        wall_ms = (time.monotonic() - wall_start) * 1000.0
        return {  # ty: ignore[invalid-return-type]
            "ok": True,
            "batch_id": batch_id,
            "source_context": source_context,
            "suggestions": created,
            "cost": {
                "llm_input_tokens": getattr(provider, "last_input_tokens", 0),
                "llm_output_tokens": getattr(provider, "last_output_tokens", 0),
                "wall_clock_ms": wall_ms,
            },
        }

    @strawberry.mutation
    def suggest_analyses(self) -> JSON:
        """Ask LLM to suggest interesting analyses given available metric tables."""
        import time
        import uuid

        from shenas_analyses.suggestion import ask_for_analysis_suggestions, validate_analysis_payload

        from app.data_catalog import _walk_metrics
        from app.hypotheses import Hypothesis
        from app.llm import get_llm_provider

        provider = get_llm_provider()
        wall_start = time.monotonic()

        metrics_catalog = [meta for meta, _plugin in _walk_metrics()]
        if not metrics_catalog:
            return {"ok": False, "error": "No metric tables found", "suggestions": []}  # ty: ignore[invalid-return-type]

        try:
            payload = ask_for_analysis_suggestions(provider, metrics_catalog)
            validate_analysis_payload(payload)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "suggestions": []}  # ty: ignore[invalid-return-type]

        batch_id = str(uuid.uuid4())[:8]
        suggestions = payload.get("suggestions", [])
        created: list[dict] = []

        for s in suggestions:
            datasets = ",".join(s.get("datasets_involved", []))
            h = Hypothesis.create_suggestion(
                question=s["question"],
                rationale=s.get("rationale", ""),
                datasets_involved=datasets,
                complexity=s.get("complexity", ""),
                model=provider.name,
            )
            created.append(
                {
                    "id": h.id,
                    "question": s["question"],
                    "rationale": s.get("rationale", ""),
                    "datasets_involved": s.get("datasets_involved", []),
                    "complexity": s.get("complexity", ""),
                }
            )

        wall_ms = (time.monotonic() - wall_start) * 1000.0
        return {  # ty: ignore[invalid-return-type]
            "ok": True,
            "batch_id": batch_id,
            "suggestions": created,
            "cost": {
                "llm_input_tokens": getattr(provider, "last_input_tokens", 0),
                "llm_output_tokens": getattr(provider, "last_output_tokens", 0),
                "wall_clock_ms": wall_ms,
            },
        }

    @strawberry.mutation
    def accept_dataset_suggestion(self, name: str) -> OkType:
        """Accept a suggested dataset: create metric table + transforms."""
        from app.models import OkResponse
        from shenas_datasets.core import Dataset

        try:
            Dataset.accept_suggestion(name)
            return OkType.from_pydantic(OkResponse(ok=True, message=f"Accepted dataset {name}"))  # ty: ignore[unresolved-attribute]
        except ValueError as exc:
            return OkType.from_pydantic(OkResponse(ok=False, message=str(exc)))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def dismiss_dataset_suggestion(self, name: str) -> OkType:
        """Dismiss a suggested dataset."""
        from app.models import OkResponse
        from shenas_datasets.core import Dataset

        try:
            Dataset.dismiss_suggestion(name)
            return OkType.from_pydantic(OkResponse(ok=True, message=f"Dismissed dataset {name}"))  # ty: ignore[unresolved-attribute]
        except ValueError as exc:
            return OkType.from_pydantic(OkResponse(ok=False, message=str(exc)))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def accept_transform_suggestion(self, transform_id: int) -> OkType:
        """Accept a suggested transform: enable it."""
        from shenas_transformers.core.transform import Transform

        from app.models import OkResponse

        t = Transform.find(transform_id)
        if t is None or not t.is_suggested:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"No suggested transform #{transform_id}"))  # ty: ignore[unresolved-attribute]
        t.accept_suggestion()
        return OkType.from_pydantic(OkResponse(ok=True, message=f"Accepted transform #{t.id}"))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def dismiss_transform_suggestion(self, transform_id: int) -> OkType:
        """Dismiss a suggested transform."""
        from shenas_transformers.core.transform import Transform

        from app.models import OkResponse

        t = Transform.find(transform_id)
        if t is None or not t.is_suggested:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"No suggested transform #{transform_id}"))  # ty: ignore[unresolved-attribute]
        t.dismiss_suggestion()
        return OkType.from_pydantic(OkResponse(ok=True, message=f"Dismissed transform #{transform_id}"))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def accept_analysis_suggestion(self, hypothesis_id: int) -> OkType:
        """Accept a suggested analysis."""
        from app.hypotheses import Hypothesis
        from app.models import OkResponse

        h = Hypothesis.find(hypothesis_id)
        if h is None or not h.is_suggested:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"No suggested analysis #{hypothesis_id}"))  # ty: ignore[unresolved-attribute]
        h.accept_suggestion()
        return OkType.from_pydantic(OkResponse(ok=True, message=f"Accepted analysis #{h.id}"))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def dismiss_analysis_suggestion(self, hypothesis_id: int) -> OkType:
        """Dismiss a suggested analysis."""
        from app.hypotheses import Hypothesis
        from app.models import OkResponse

        h = Hypothesis.find(hypothesis_id)
        if h is None or not h.is_suggested:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"No suggested analysis #{hypothesis_id}"))  # ty: ignore[unresolved-attribute]
        h.dismiss_suggestion()
        return OkType.from_pydantic(OkResponse(ok=True, message=f"Dismissed analysis #{hypothesis_id}"))  # ty: ignore[unresolved-attribute]

    # -- Entities --

    @strawberry.mutation
    def create_entity(self, entity_input: EntityCreateInput) -> GqlEntityType:
        from app.entity import Entity

        e = Entity.create(
            type=entity_input.type,
            name=entity_input.name,
            description=entity_input.description,
            status=entity_input.status,
        )
        me_candidates = Entity.all(where="type = 'human'", order_by="id", limit=1)
        me_uuid = me_candidates[0].uuid if me_candidates else None
        return GqlEntityType(
            uuid=e.uuid,
            type=e.type,
            name=e.name,
            description=e.description,
            status=e.status,
            added_at=str(e.added_at) if e.added_at else None,
            updated_at=str(e.updated_at) if e.updated_at else None,
            is_me=(e.uuid == me_uuid),
        )

    @strawberry.mutation
    def update_entity(self, uuid: str, entity_input: EntityUpdateInput) -> GqlEntityType | None:
        from app.entity import Entity

        e = Entity.find_by_uuid(uuid)
        if e is None:
            return None
        if entity_input.name is not None:
            e.name = entity_input.name
        if entity_input.type is not None:
            e.type = entity_input.type
        if entity_input.description is not None:
            e.description = entity_input.description
        if entity_input.status is not None:
            e.status = entity_input.status
        e.save()
        me_candidates = Entity.all(where="type = 'human'", order_by="id", limit=1)
        me_uuid = me_candidates[0].uuid if me_candidates else None
        return GqlEntityType(
            uuid=e.uuid,
            type=e.type,
            name=e.name,
            description=e.description,
            status=e.status,
            added_at=str(e.added_at) if e.added_at else None,
            updated_at=str(e.updated_at) if e.updated_at else None,
            is_me=(e.uuid == me_uuid),
        )

    @strawberry.mutation
    def delete_entity(self, uuid: str) -> OkType:
        from app.entity import Entity
        from app.models import OkResponse

        e = Entity.find_by_uuid(uuid)
        if e is None:
            return OkType.from_pydantic(OkResponse(ok=False, message="Entity not found"))  # ty: ignore[unresolved-attribute]
        e.delete()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def set_entity_status(self, uuid: str, status: str) -> OkType:
        """Update the enabled/disabled status of an entity (user or virtual).

        For virtual entities the status is stored on ``entity_index``; for
        user-created entities we also keep the matching ``entities`` row in
        sync.
        """
        from app.entity import Entity, EntityIndex
        from app.models import OkResponse

        if status not in ("enabled", "disabled"):
            return OkType.from_pydantic(  # ty: ignore[unresolved-attribute]
                OkResponse(ok=False, message=f"Invalid status: {status!r}"),
            )
        idx = EntityIndex.find(uuid)
        if idx is None:
            return OkType.from_pydantic(  # ty: ignore[unresolved-attribute]
                OkResponse(ok=False, message="Entity not found"),
            )
        idx.status = status
        idx.save()
        entity = Entity.find_by_uuid(uuid)
        if entity is not None:
            entity.status = status
            entity.save()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def set_entity_mapping(self, source_table: str, source_row_key: str, target_uuid: str | None = None) -> OkType:
        """Map a row from an ``EntityMapTable`` to a real entity UUID.

        Passing ``target_uuid=None`` removes any existing mapping. The
        ``(source_table, source_row_key)`` pair is the PK of ``entity_mappings``.
        """
        from app.entity import EntityMapping
        from app.models import OkResponse

        existing = EntityMapping.find(source_table, source_row_key)
        if target_uuid is None or target_uuid == "":
            if existing is not None:
                existing.delete()
            return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]
        if existing is None:
            EntityMapping(
                source_table=source_table,
                source_row_key=source_row_key,
                target_uuid=target_uuid,
            ).insert()
        else:
            existing.target_uuid = target_uuid
            existing.save()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]

    @strawberry.mutation
    def create_entity_relationship(
        self, from_uuid: str, to_uuid: str, relationship_type: str, description: str = ""
    ) -> GqlEntityRelationshipType:
        from app.entity import EntityRelationship

        r = EntityRelationship(from_uuid=from_uuid, to_uuid=to_uuid, type=relationship_type, description=description)
        r.upsert()
        return GqlEntityRelationshipType(
            from_uuid=r.from_uuid,
            to_uuid=r.to_uuid,
            type=r.type,
            description=r.description,
            added_at=str(r.added_at) if r.added_at else None,
            updated_at=str(r.updated_at) if r.updated_at else None,
        )

    @strawberry.mutation
    def delete_entity_relationship(self, from_uuid: str, to_uuid: str, relationship_type: str) -> OkType:
        from app.entity import EntityRelationship
        from app.models import OkResponse

        r = EntityRelationship.find(from_uuid, to_uuid, relationship_type)
        if r is None:
            return OkType.from_pydantic(OkResponse(ok=False, message="Relationship not found"))  # ty: ignore[unresolved-attribute]
        r.delete()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]
