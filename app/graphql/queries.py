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
    def device_name(self) -> str:
        try:
            from app.mesh.identity import get_device_info

            return get_device_info()["device_name"]
        except Exception:
            return ""

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

    # -- Plugins --

    @strawberry.field
    def plugins(self, kind: str) -> list[PluginInfoType]:
        from app.api.plugins import list_plugins_data

        items = list_plugins_data(kind)
        return [PluginInfoType.from_pydantic(p) for p in items]

    @strawberry.field
    def plugin_info(self, kind: str, name: str) -> JSON:
        from app.api.sources import _load_plugin, _load_plugin_fresh

        cls = _load_plugin(kind, name) or _load_plugin_fresh(kind, name)
        if not cls:
            return {"name": name, "kind": kind, "display_name": name.replace("-", " ").title()}
        return cls().get_info()

    @strawberry.field
    def available_plugins(self, kind: str) -> list[str]:
        """List plugin names available on the repository server for a given kind."""
        import re
        from html.parser import HTMLParser
        from urllib.request import urlopen

        from app.api.plugins import DEFAULT_INDEX

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
    def dashboards(self) -> JSON:
        from app.api.sources import _load_dashboards
        from app.db import is_plugin_enabled

        return [
            {
                "name": c.name,
                "display_name": c.display_name,
                "tag": c.tag,
                "js": f"/dashboards/{c.name}/{c.entrypoint}",
                "description": c.description,
            }
            for c in _load_dashboards(include_internal=False)
            if is_plugin_enabled("dashboard", c.name)
        ]

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
