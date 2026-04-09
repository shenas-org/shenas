"""GraphQL Mutation resolvers."""

from __future__ import annotations

import json

import strawberry
from strawberry.scalars import JSON  # noqa: TC002 - needed at runtime by Strawberry

from app.graphql.queries import _transform_to_gql
from app.graphql.types import (
    AuthResponseType,
    InstallResponseType,
    OkType,
    RemoveResponseType,
    TransformCreateInput,
    TransformType,
)


def _source_entry_point_names() -> list[str]:
    """Return names of all installed source plugins."""
    from importlib.metadata import entry_points

    return [ep.name for ep in entry_points(group="shenas.sources")]


def _build_catalog() -> dict[str, dict]:
    """Return ``{qualified_table: table_metadata}`` for the recipe runner.

    Thin wrapper over :func:`app.analytics_catalog.catalog_by_qualified_name`,
    which is the shared walk used by the GraphQL ``catalog`` query too.
    """
    from app.analytics_catalog import catalog_by_qualified_name

    return catalog_by_qualified_name()


@strawberry.type
class Mutation:
    # -- Auth --

    @strawberry.mutation
    def authenticate(self, pipe: str, credentials: JSON) -> AuthResponseType:
        from app.api.sources import _load_source
        from app.models import AuthResponse

        p = _load_source(pipe)
        result = p.handle_auth(credentials)
        return AuthResponseType.from_pydantic(AuthResponse(**result))

    # -- Config --

    @strawberry.mutation
    def set_config(self, kind: str, name: str, key: str, value: str) -> OkType:
        from app.api.sources import _load_plugin
        from app.models import OkResponse

        cls = _load_plugin(kind, name)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))
        plugin = cls()
        plugin.set_config_value(key, value)
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def delete_config(self, kind: str, name: str) -> OkType:
        from app.api.sources import _load_plugin
        from app.models import OkResponse

        cls = _load_plugin(kind, name)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))
        cls().delete_config()
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def delete_config_key(self, kind: str, name: str, key: str) -> OkType:
        from app.api.sources import _load_plugin
        from app.models import OkResponse

        cls = _load_plugin(kind, name)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))
        cls().set_config_value(key, None)
        return OkType.from_pydantic(OkResponse(ok=True))

    # -- Database --

    @strawberry.mutation
    def generate_db_key(self) -> OkType:
        from app.db import generate_db_key, set_db_key
        from app.models import OkResponse

        key = generate_db_key()
        set_db_key(key)
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def flush_schema(self, schema_plugin: str) -> JSON:
        from app.api.db import flush_schema

        return flush_schema(schema_plugin)

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
        from shenas_plugins.core.plugin import DEFAULT_INDEX, Plugin

        results = []
        for n in names:
            ok, message = Plugin.install(kind, n, index_url=index_url or DEFAULT_INDEX, skip_verify=skip_verify)
            results.append(InstallResult(name=n, ok=ok, message=message))
        return InstallResponseType.from_pydantic(InstallResponse(results=results))

    @strawberry.mutation
    def remove_plugin(self, kind: str, name: str) -> RemoveResponseType:
        from app.models import RemoveResponse
        from shenas_plugins.core.plugin import Plugin

        ok, message = Plugin.uninstall(kind, name)
        return RemoveResponseType.from_pydantic(RemoveResponse(ok=ok, message=message))

    @strawberry.mutation
    def enable_plugin(self, kind: str, name: str) -> OkType:
        from app.models import OkResponse
        from shenas_plugins.core.plugin import PluginInstance

        inst = PluginInstance.get_or_create(kind, name)
        msg = inst.enable()
        return OkType.from_pydantic(OkResponse(ok=True, message=msg))

    @strawberry.mutation
    def disable_plugin(self, kind: str, name: str) -> OkType:
        from app.models import OkResponse
        from shenas_plugins.core.plugin import PluginInstance

        inst = PluginInstance.find(kind, name)
        if not inst:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not tracked: {kind}/{name}"))
        msg = inst.disable()
        return OkType.from_pydantic(OkResponse(ok=True, message=msg))

    # -- Transforms --

    @strawberry.mutation
    def create_transform(self, transform_input: TransformCreateInput) -> TransformType:
        from shenas_transformations.core.instance import TransformInstance

        t = TransformInstance.create(
            transform_type=transform_input.transform_type,
            source_duckdb_schema=transform_input.source_duckdb_schema,
            source_duckdb_table=transform_input.source_duckdb_table,
            target_duckdb_schema=transform_input.target_duckdb_schema,
            target_duckdb_table=transform_input.target_duckdb_table,
            source_plugin=transform_input.source_plugin,
            params=transform_input.params,
            description=transform_input.description,
        )
        return _transform_to_gql(t)

    @strawberry.mutation
    def update_transform(self, transform_id: int, params: str) -> TransformType | None:
        from shenas_transformations.core.instance import TransformInstance

        existing = TransformInstance.find(transform_id)
        if not existing:
            return None
        t = existing.update_params(params)
        return _transform_to_gql(t) if t else None

    @strawberry.mutation
    def delete_transform(self, transform_id: int) -> OkType:
        from shenas_transformations.core.instance import TransformInstance

        from app.models import OkResponse

        t = TransformInstance.find(transform_id)
        if t:
            t.delete()
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def enable_transform(self, transform_id: int) -> TransformType | None:
        from shenas_transformations.core.instance import TransformInstance

        t = TransformInstance.find(transform_id)
        if not t:
            return None
        updated = t.set_enabled(True)
        return _transform_to_gql(updated) if updated else None

    @strawberry.mutation
    def disable_transform(self, transform_id: int) -> TransformType | None:
        from shenas_transformations.core.instance import TransformInstance

        t = TransformInstance.find(transform_id)
        if not t:
            return None
        updated = t.set_enabled(False)
        return _transform_to_gql(updated) if updated else None

    @strawberry.mutation
    def test_transform(self, transform_id: int, limit: int = 10) -> JSON:
        from shenas_transformations.core.instance import TransformInstance

        t = TransformInstance.find(transform_id)
        return t.test(limit) if t else []

    @strawberry.mutation
    def seed_transforms(self) -> JSON:
        from shenas_transformations.core import Transformation

        from app.api.sources import _load_plugins

        seeded: list[str] = []
        plugins = _load_plugins("transformation", base=Transformation, include_internal=True)
        for ep_name in _source_entry_point_names():
            for cls in plugins:
                plugin = cls()
                if plugin.enabled:
                    plugin.seed_defaults_for_source(ep_name)
            seeded.append(ep_name)
        return {"seeded": seeded, "count": len(seeded)}

    @strawberry.mutation
    def run_pipe_transforms(self, pipe: str) -> JSON:
        from shenas_transformations.core.instance import TransformInstance

        from app.db import connect

        count = TransformInstance.run_for_source(connect(), pipe)
        return {"source": pipe, "count": count}

    @strawberry.mutation
    def run_schema_transforms(self, schema: str) -> JSON:
        from shenas_transformations.core.instance import TransformInstance

        from app.db import connect

        count = TransformInstance.run_for_target(connect(), schema)
        return {"schema": schema, "count": count}

    # -- Hotkeys --

    @strawberry.mutation
    def set_hotkey(self, action_id: str, binding: str, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        Hotkey(action_id=action_id).set_binding(binding)
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def delete_hotkey(self, action_id: str, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        Hotkey(action_id=action_id).delete()
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def reset_hotkeys(self, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        Hotkey.reset()
        return OkType.from_pydantic(OkResponse(ok=True))

    # -- Workspace --

    @strawberry.mutation
    def save_workspace(self, data: JSON, info: strawberry.types.Info) -> OkType:  # noqa: ARG002
        from app.models import OkResponse
        from app.workspace import Workspace

        Workspace.put(data)
        return OkType.from_pydantic(OkResponse(ok=True))

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
        from app.hypotheses import Hypothesis
        from shenas_plugins.core.analytics import Recipe

        empty = Recipe(nodes={}, final="")
        h = Hypothesis.create(question, empty, plan=plan, model=model, mode=mode)
        return {"id": h.id, "question": h.question, "mode": h.mode}

    @strawberry.mutation
    def run_recipe(self, hypothesis_id: int, recipe_json: str) -> JSON:
        """Attach a recipe DAG (JSON) to a hypothesis, run it, persist the result.

        ``recipe_json`` is the same shape Hypothesis._serialize_recipe
        emits: ``{"nodes": {name: {type, ...}}, "final": str}``.
        """
        import json

        from app.db import analytics_backend
        from app.hypotheses import Hypothesis, _extract_input_tables, _serialize_recipe
        from shenas_plugins.core.analytics import (
            ErrorResult,
            OpCall,
            Recipe,
            SourceRef,
            run_recipe,
        )

        h = Hypothesis.find(hypothesis_id)
        if h is None:
            return {"error": f"hypothesis {hypothesis_id} not found"}

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
            return {"id": h.id, "result": cached, "ok": cached.get("type") != "error", "cached": True}

        result = run_recipe(recipe, catalog, backend=analytics_backend())
        h.attach_result(result)
        if not isinstance(result, ErrorResult):
            RecipeCache.put(cache_key, result.model_dump())
        return {
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
            return {"error": f"hypothesis {hypothesis_id} not found"}

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
        return {"id": fork.id, "parent_id": parent.id, "question": fork.question}

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
            return {"error": f"hypothesis {hypothesis_id} not found"}
        try:
            record = _promote(h, name=name, metric_schema=metric_schema)
        except ValueError as exc:
            return {"error": str(exc)}
        return {
            "id": h.id,
            "promoted_to": h.promoted_to,
            "qualified": record.qualified,
        }

    # -- LLM-driven hypothesis --

    @strawberry.mutation
    def ask_hypothesis(self, question: str, mode: str = "hypothesis") -> JSON:  # noqa: PLR0915 -- linear narrative is clearer than splitting
        """End-to-end: create a hypothesis, ask the LLM for a recipe, run it, persist.

        The LLM provider is constructed from environment / settings; the
        default is :class:`AnthropicProvider` which reads
        ``ANTHROPIC_API_KEY``. The ``mode`` parameter selects which
        analysis strategy the LLM uses (operation vocabulary, system
        prompt framing). Returns the hypothesis id, the LLM's plan,
        the recipe payload, the run result, and a per-turn cost block
        (input/output tokens, llm/query/wall_clock elapsed ms).
        """
        import time

        # Ensure built-in modes are registered.
        import shenas_plugins.core.analytics.modes  # noqa: F401
        from app.db import analytics_backend
        from app.graphql.llm_provider import get_llm_provider
        from app.hypotheses import Hypothesis, _extract_input_tables, _serialize_recipe
        from shenas_plugins.core.analytics import (
            ErrorResult,
            OpCall,
            Recipe,
            SourceRef,
            ask_for_recipe_with_retry,
            run_recipe,
        )
        from shenas_plugins.core.analytics.mode import get_mode

        try:
            analysis_mode = get_mode(mode)
        except KeyError as exc:
            return {"ok": False, "error": {"message": str(exc)}}

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
            Recipe(nodes=tmp_nodes, final=p.get("final", "")).validate()

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
            return {"id": h.id, "ok": False, "error": err}
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
        return {
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
