"""GraphQL Mutation resolvers."""

from __future__ import annotations

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
        from app.api.sources import _load_plugin
        from app.models import OkResponse

        cls = _load_plugin(kind, name)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))
        msg = cls().enable()
        return OkType.from_pydantic(OkResponse(ok=True, message=msg))

    @strawberry.mutation
    def disable_plugin(self, kind: str, name: str) -> OkType:
        from app.api.sources import _load_plugin
        from app.models import OkResponse

        cls = _load_plugin(kind, name)
        if not cls:
            return OkType.from_pydantic(OkResponse(ok=False, message=f"Plugin not found: {kind}/{name}"))
        msg = cls().disable()
        return OkType.from_pydantic(OkResponse(ok=True, message=msg))

    # -- Transforms --

    @strawberry.mutation
    def create_transform(self, transform_input: TransformCreateInput) -> TransformType:
        from app.transforms import Transform

        t = Transform.create(
            source_duckdb_schema=transform_input.source_duckdb_schema,
            source_duckdb_table=transform_input.source_duckdb_table,
            target_duckdb_schema=transform_input.target_duckdb_schema,
            target_duckdb_table=transform_input.target_duckdb_table,
            source_plugin=transform_input.source_plugin,
            sql=transform_input.sql,
            description=transform_input.description,
        )
        return _transform_to_gql(t)

    @strawberry.mutation
    def update_transform(self, transform_id: int, sql: str) -> TransformType | None:
        from app.transforms import Transform

        existing = Transform.find(transform_id)
        if not existing:
            return None
        t = existing.update(sql)
        return _transform_to_gql(t) if t else None

    @strawberry.mutation
    def delete_transform(self, transform_id: int) -> OkType:
        from app.models import OkResponse
        from app.transforms import Transform

        t = Transform.find(transform_id)
        if t:
            t.delete()
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def enable_transform(self, transform_id: int) -> TransformType | None:
        from app.transforms import Transform

        t = Transform.find(transform_id)
        if not t:
            return None
        updated = t.set_enabled(True)
        return _transform_to_gql(updated) if updated else None

    @strawberry.mutation
    def disable_transform(self, transform_id: int) -> TransformType | None:
        from app.transforms import Transform

        t = Transform.find(transform_id)
        if not t:
            return None
        updated = t.set_enabled(False)
        return _transform_to_gql(updated) if updated else None

    @strawberry.mutation
    def test_transform(self, transform_id: int, limit: int = 10) -> JSON:
        from app.transforms import Transform

        t = Transform.find(transform_id)
        return t.test(limit) if t else []

    @strawberry.mutation
    def seed_transforms(self) -> JSON:
        from importlib.metadata import entry_points

        from app.transforms import Transform
        from shenas_sources.core.transform import load_transform_defaults

        seeded: list[str] = []
        for ep in entry_points(group="shenas.sources"):
            defaults = load_transform_defaults(ep.name)
            if defaults:
                Transform.seed_defaults(ep.name, defaults)
                seeded.append(ep.name)
        return {"seeded": seeded, "count": len(seeded)}

    @strawberry.mutation
    def run_pipe_transforms(self, pipe: str) -> JSON:
        from app.db import connect
        from app.transforms import Transform

        count = Transform.run_for_source(connect(), pipe)
        return {"source": pipe, "count": count}

    @strawberry.mutation
    def run_schema_transforms(self, schema: str) -> JSON:
        from app.db import connect
        from app.transforms import Transform

        count = Transform.run_for_target(connect(), schema)
        return {"schema": schema, "count": count}

    # -- Hotkeys --

    @strawberry.mutation
    def set_hotkey(self, info: strawberry.types.Info, action_id: str, binding: str) -> OkType:
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        user_id = info.context.get("user_id", 0) or 0
        Hotkey(action_id, user_id=user_id).set(binding)
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def delete_hotkey(self, info: strawberry.types.Info, action_id: str) -> OkType:
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        user_id = info.context.get("user_id", 0) or 0
        Hotkey(action_id, user_id=user_id).delete()
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def reset_hotkeys(self, info: strawberry.types.Info) -> OkType:
        from app.hotkeys import Hotkey
        from app.models import OkResponse

        user_id = info.context.get("user_id", 0) or 0
        Hotkey.reset(user_id=user_id)
        return OkType.from_pydantic(OkResponse(ok=True))

    # -- Workspace --

    @strawberry.mutation
    def save_workspace(self, info: strawberry.types.Info, data: JSON) -> OkType:
        from app.models import OkResponse
        from app.workspace import Workspace

        user_id = info.context.get("user_id", 0) or 0
        Workspace.save(data, user_id=user_id)
        return OkType.from_pydantic(OkResponse(ok=True))
