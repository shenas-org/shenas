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
        from app.api.pipes import _load_pipe
        from app.models import AuthResponse

        p = _load_pipe(pipe)
        result = p.handle_auth(credentials)
        return AuthResponseType.from_pydantic(AuthResponse(**result))

    # -- Config --

    @strawberry.mutation
    def set_config(self, kind: str, name: str, key: str, value: str) -> OkType:
        from app.api.config import _resolve_plugin
        from app.models import OkResponse

        plugin = _resolve_plugin(kind, name)
        plugin.set_config_value(key, value)
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def delete_config(self, kind: str, name: str) -> OkType:
        from app.api.config import _resolve_plugin
        from app.models import OkResponse

        plugin = _resolve_plugin(kind, name)
        plugin.delete_config()
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def delete_config_key(self, kind: str, name: str, key: str) -> OkType:
        from app.api.config import _resolve_plugin
        from app.models import OkResponse

        plugin = _resolve_plugin(kind, name)
        plugin.set_config_value(key, None)
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
        from app.api.plugins import DEFAULT_INDEX, install_plugin
        from app.models import InstallResponse

        results = [install_plugin(n, kind, index_url=index_url or DEFAULT_INDEX, skip_verify=skip_verify) for n in names]
        return InstallResponseType.from_pydantic(InstallResponse(results=results))

    @strawberry.mutation
    def remove_plugin(self, kind: str, name: str) -> RemoveResponseType:
        from app.api.plugins import uninstall_plugin

        result = uninstall_plugin(name, kind)
        return RemoveResponseType.from_pydantic(result)

    @strawberry.mutation
    def enable_plugin(self, kind: str, name: str) -> OkType:
        from app.api.plugins import enable_plugin

        result = enable_plugin(kind, name)
        return OkType.from_pydantic(result)

    @strawberry.mutation
    def disable_plugin(self, kind: str, name: str) -> OkType:
        from app.api.plugins import disable_plugin

        result = disable_plugin(kind, name)
        return OkType.from_pydantic(result)

    # -- Transforms --

    @strawberry.mutation
    def create_transform(self, transform_input: TransformCreateInput) -> TransformType:
        from app.transforms import create_transform

        t = create_transform(
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
        from app.transforms import get_transform, update_transform

        existing = get_transform(transform_id)
        if not existing:
            return None
        t = update_transform(transform_id, sql)
        return _transform_to_gql(t) if t else None

    @strawberry.mutation
    def delete_transform(self, transform_id: int) -> OkType:
        from app.models import OkResponse
        from app.transforms import delete_transform

        delete_transform(transform_id)
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def enable_transform(self, transform_id: int) -> TransformType | None:
        from app.transforms import set_transform_enabled

        t = set_transform_enabled(transform_id, enabled=True)
        return _transform_to_gql(t) if t else None

    @strawberry.mutation
    def disable_transform(self, transform_id: int) -> TransformType | None:
        from app.transforms import set_transform_enabled

        t = set_transform_enabled(transform_id, enabled=False)
        return _transform_to_gql(t) if t else None

    @strawberry.mutation
    def test_transform(self, transform_id: int, limit: int = 10) -> JSON:
        from app.transforms import test_transform

        return test_transform(transform_id, limit)

    @strawberry.mutation
    def seed_transforms(self) -> JSON:
        from importlib.metadata import entry_points

        from app.transforms import seed_defaults
        from shenas_pipes.core.transform import load_transform_defaults

        seeded: list[str] = []
        for ep in entry_points(group="shenas.pipes"):
            defaults = load_transform_defaults(ep.name)
            if defaults:
                seed_defaults(ep.name, defaults)
                seeded.append(ep.name)
        return {"seeded": seeded, "count": len(seeded)}

    @strawberry.mutation
    def run_pipe_transforms(self, pipe: str) -> JSON:
        from app.db import connect
        from app.transforms import run_transforms

        con = connect()
        count = run_transforms(con, pipe)
        return {"pipe": pipe, "count": count}

    @strawberry.mutation
    def run_schema_transforms(self, schema: str) -> JSON:
        from app.db import connect
        from app.transforms import run_transforms_by_target

        con = connect()
        count = run_transforms_by_target(con, schema)
        return {"schema": schema, "count": count}

    # -- Hotkeys --

    @strawberry.mutation
    def set_hotkey(self, action_id: str, binding: str) -> OkType:
        from app.db import set_hotkey
        from app.models import OkResponse

        set_hotkey(action_id, binding)
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def delete_hotkey(self, action_id: str) -> OkType:
        from app.db import set_hotkey
        from app.models import OkResponse

        set_hotkey(action_id, "")
        return OkType.from_pydantic(OkResponse(ok=True))

    @strawberry.mutation
    def reset_hotkeys(self) -> OkType:
        from app.db import reset_hotkeys
        from app.models import OkResponse

        reset_hotkeys()
        return OkType.from_pydantic(OkResponse(ok=True))

    # -- Workspace --

    @strawberry.mutation
    def save_workspace(self, data: JSON) -> OkType:
        from app.db import save_workspace
        from app.models import OkResponse

        save_workspace(data)
        return OkType.from_pydantic(OkResponse(ok=True))
