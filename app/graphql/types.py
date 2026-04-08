"""Strawberry GraphQL types -- wraps existing Pydantic models."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON

from app.models import (
    AuthField,
    AuthFieldsResponse,
    AuthResponse,
    ConfigEntry,
    DBStatusResponse,
    InstallResponse,
    InstallResult,
    OkResponse,
    PluginInfo,
    RemoveResponse,
    ScheduleInfo,
    SchemaInfo,
    TableStats,
)

# -- Wrapped Pydantic types --------------------------------------------------


@strawberry.experimental.pydantic.type(model=OkResponse, all_fields=True)
class OkType:
    pass


@strawberry.experimental.pydantic.type(model=AuthField, all_fields=True)
class AuthFieldType:
    pass


@strawberry.experimental.pydantic.type(model=AuthFieldsResponse, all_fields=True)
class AuthFieldsType:
    pass


@strawberry.experimental.pydantic.type(model=AuthResponse, all_fields=True)
class AuthResponseType:
    pass


@strawberry.experimental.pydantic.type(model=ConfigEntry, all_fields=True)
class ConfigEntryType:
    pass


@strawberry.experimental.pydantic.type(model=TableStats, all_fields=True)
class TableStatsType:
    pass


@strawberry.experimental.pydantic.type(model=SchemaInfo, all_fields=True)
class SchemaInfoType:
    pass


@strawberry.experimental.pydantic.type(model=DBStatusResponse, all_fields=True)
class DBStatusType:
    pass


@strawberry.experimental.pydantic.type(model=PluginInfo, all_fields=True)
class PluginInfoType:
    pass


@strawberry.experimental.pydantic.type(model=InstallResult, all_fields=True)
class InstallResultType:
    pass


@strawberry.experimental.pydantic.type(model=InstallResponse, all_fields=True)
class InstallResponseType:
    pass


@strawberry.experimental.pydantic.type(model=RemoveResponse, all_fields=True)
class RemoveResponseType:
    pass


@strawberry.experimental.pydantic.type(model=ScheduleInfo, all_fields=True)
class ScheduleInfoType:
    pass


# -- New types (not from Pydantic) --------------------------------------------


@strawberry.type
class TableEntry:
    schema_name: str = strawberry.field(name="schema")
    table: str


@strawberry.type
class ThemeInfo:
    name: str | None
    css: str | None


@strawberry.type
class TransformType:
    id: int
    source_duckdb_schema: str
    source_duckdb_table: str
    target_duckdb_schema: str
    target_duckdb_table: str
    source_plugin: str
    description: str
    sql: str
    is_default: bool
    enabled: bool
    created_at: str | None
    updated_at: str | None
    status_changed_at: str | None
    deleted_at: str | None


# -- Input types --------------------------------------------------------------


@strawberry.input
class TransformCreateInput:
    source_duckdb_schema: str
    source_duckdb_table: str
    target_duckdb_schema: str
    target_duckdb_table: str
    source_plugin: str
    sql: str
    description: str = ""


__all__ = [
    "JSON",
    "AuthFieldType",
    "AuthFieldsType",
    "AuthResponseType",
    "ConfigEntryType",
    "DBStatusType",
    "InstallResponseType",
    "InstallResultType",
    "OkType",
    "PluginInfoType",
    "RemoveResponseType",
    "ScheduleInfoType",
    "SchemaInfoType",
    "TableEntry",
    "TableStatsType",
    "ThemeInfo",
    "TransformCreateInput",
    "TransformType",
]
