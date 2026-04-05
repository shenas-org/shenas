"""GraphQL Query resolvers."""

from __future__ import annotations

from typing import Any

import strawberry
from strawberry.scalars import JSON  # noqa: TC002 - needed at runtime by Strawberry

from app.graphql.types import (
    AuthFieldsType,
    ConfigItemType,
    DBStatusType,
    PluginInfoType,
    ScheduleInfoType,
    TableEntry,
    ThemeInfo,
    TransformType,
)


def _transform_to_gql(t: dict[str, Any]) -> TransformType:
    return TransformType(
        id=t["id"],
        source_duckdb_schema=t["source_duckdb_schema"],
        source_duckdb_table=t["source_duckdb_table"],
        target_duckdb_schema=t["target_duckdb_schema"],
        target_duckdb_table=t["target_duckdb_table"],
        source_plugin=t["source_plugin"],
        description=t.get("description", ""),
        sql=t["sql"],
        is_default=t["is_default"],
        enabled=t["enabled"],
        added_at=t.get("added_at"),
        updated_at=t.get("updated_at"),
        status_changed_at=t.get("status_changed_at"),
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
        return AuthFieldsType.from_pydantic(result)

    # -- Config --

    @strawberry.field
    def config(self, kind: str | None = None, name: str | None = None) -> list[ConfigItemType]:
        from app.api.config import list_configs

        items = list_configs(kind=kind, name=name)
        return [ConfigItemType.from_pydantic(c) for c in items]

    @strawberry.field
    def config_value(self, kind: str, name: str, key: str) -> str | None:
        from app.api.config import get_config_value

        try:
            result = get_config_value(kind, name, key)
            return result.value
        except Exception:
            return None

    # -- Database --

    @strawberry.field
    def db_status(self) -> DBStatusType:
        from app.api.db import db_status

        return DBStatusType.from_pydantic(db_status())

    @strawberry.field
    def db_tables(self) -> JSON:
        from app.api.db import db_tables

        return db_tables()

    @strawberry.field
    def schema_tables(self) -> JSON:
        from app.api.db import schema_plugin_tables

        return schema_plugin_tables()

    @strawberry.field
    def schema_plugins(self) -> JSON:
        from app.api.db import schema_plugin_ownership

        return schema_plugin_ownership()

    @strawberry.field
    def table_preview(self, schema: str, table: str, limit: int = 50) -> JSON:
        from app.api.db import table_preview

        return table_preview(schema, table, limit)

    # -- Plugins --

    @strawberry.field
    def plugins(self, kind: str) -> list[PluginInfoType]:
        from app.api.plugins import list_plugins_data

        items = list_plugins_data(kind)
        return [PluginInfoType.from_pydantic(p) for p in items]

    @strawberry.field
    def plugin_info(self, kind: str, name: str) -> JSON:
        from app.api.pipes import _load_plugin

        cls = _load_plugin(kind, name)
        if not cls:
            return None
        return cls().get_info()

    # -- Sync --

    @strawberry.field
    def sync_schedule(self) -> list[ScheduleInfoType]:
        from app.db import get_all_sync_schedules

        rows = get_all_sync_schedules()
        from app.models import ScheduleInfo

        return [ScheduleInfoType.from_pydantic(ScheduleInfo(**row)) for row in rows]

    # -- Transforms --

    @strawberry.field
    def transforms(self, source: str | None = None) -> list[TransformType]:
        from app.transforms import list_transforms

        return [_transform_to_gql(t) for t in list_transforms(source)]

    @strawberry.field
    def transform(self, transform_id: int) -> TransformType | None:
        from app.transforms import get_transform

        t = get_transform(transform_id)
        return _transform_to_gql(t) if t else None

    # -- Theme --

    @strawberry.field
    def theme(self) -> ThemeInfo:
        from app.server import _get_active_theme

        t = _get_active_theme()
        if t:
            return ThemeInfo(name=t.name, css=f"/themes/{t.name}/{t.css}")
        return ThemeInfo(name=None, css=None)

    # -- Telemetry --

    @strawberry.field
    def logs(
        self,
        limit: int = 100,
        severity: str | None = None,
        search: str | None = None,
        pipe: str | None = None,
    ) -> JSON:
        from app.db import connect

        limit = max(1, min(limit, 1000))
        con = connect(read_only=True)
        cur = con.cursor()
        try:
            cur.execute("USE db")
            conditions: list[str] = []
            params: list[Any] = []
            if severity:
                conditions.append("severity = ?")
                params.append(severity)
            if search:
                conditions.append("body LIKE ?")
                params.append(f"%{search}%")
            if pipe:
                conditions.append("(body LIKE ? OR attributes LIKE ?)")
                params.extend([f"%{pipe}%", f"%{pipe}%"])
            where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
            rows = cur.execute(
                f"SELECT timestamp, trace_id, span_id, severity, body, attributes, service_name "
                f"FROM telemetry.logs{where} ORDER BY timestamp DESC LIMIT {limit}",
                params,
            ).fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r, strict=False)) for r in rows]
        except Exception:
            return []
        finally:
            cur.close()

    @strawberry.field
    def spans(
        self,
        limit: int = 100,
        search: str | None = None,
        pipe: str | None = None,
    ) -> JSON:
        from app.db import connect

        limit = max(1, min(limit, 1000))
        con = connect(read_only=True)
        cur = con.cursor()
        try:
            cur.execute("USE db")
            conditions: list[str] = []
            params: list[Any] = []
            if search:
                conditions.append("name LIKE ?")
                params.append(f"%{search}%")
            if pipe:
                conditions.append("(name LIKE ? OR attributes LIKE ?)")
                params.extend([f"%{pipe}%", f"%{pipe}%"])
            where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
            rows = cur.execute(
                f"SELECT trace_id, span_id, parent_span_id, name, kind, service_name, "
                f"status_code, start_time, end_time, duration_ms, attributes "
                f"FROM telemetry.spans{where} ORDER BY start_time DESC LIMIT {limit}",
                params,
            ).fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r, strict=False)) for r in rows]
        except Exception:
            return []
        finally:
            cur.close()

    # -- App-level --

    @strawberry.field
    def hotkeys(self) -> JSON:
        from app.db import get_hotkeys

        return get_hotkeys()

    @strawberry.field
    def workspace(self) -> JSON:
        from app.db import get_workspace

        return get_workspace()

    @strawberry.field
    def components(self) -> JSON:
        from app.api.pipes import _load_components
        from app.db import is_plugin_enabled

        return [
            {
                "name": c.name,
                "display_name": c.display_name,
                "tag": c.tag,
                "js": f"/components/{c.name}/{c.entrypoint}",
                "description": c.description,
            }
            for c in _load_components(include_internal=False)
            if is_plugin_enabled("component", c.name)
        ]

    @strawberry.field
    def dependencies(self) -> JSON:
        from importlib.metadata import distributions

        prefixes = {
            "shenas-pipe-": "pipe",
            "shenas-schema-": "schema",
            "shenas-component-": "component",
            "shenas-ui-": "ui",
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
        return result

    # -- Models --

    @strawberry.field
    def models(self) -> JSON:
        from app.api.models import list_models

        return list_models()

    @strawberry.field
    def model_status(self, name: str) -> JSON:
        from app.api.models import model_status

        return model_status(name)

    @strawberry.field
    def model_predict(self, name: str) -> JSON:
        from app.api.models import predict

        return predict(name)
