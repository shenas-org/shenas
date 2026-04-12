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
    transform_type: str
    source_duckdb_schema: str
    source_duckdb_table: str
    target_duckdb_schema: str
    target_duckdb_table: str
    source_plugin: str
    params: str
    description: str
    is_default: bool
    enabled: bool
    added_at: str | None
    updated_at: str | None
    status_changed_at: str | None

    @strawberry.field
    def sql(self) -> str:
        """Extract SQL from params JSON for convenience."""
        import json

        try:
            return json.loads(self.params).get("sql", "")
        except (json.JSONDecodeError, TypeError):
            return ""


# -- Input types --------------------------------------------------------------


@strawberry.input
class TransformCreateInput:
    transform_type: str
    source_duckdb_schema: str
    source_duckdb_table: str
    target_duckdb_schema: str
    target_duckdb_table: str
    source_plugin: str
    params: str = "{}"
    description: str = ""


# -- Data Catalog types --------------------------------------------------------


@strawberry.type
class DataResourceRefType:
    id: str
    schema_name: str
    table_name: str


@strawberry.type
class ColumnInfoType:
    name: str
    db_type: str
    nullable: bool
    description: str
    unit: str | None = None
    value_range: list[float] | None = None
    example_value: str | None = None
    interpretation: str | None = None


@strawberry.type
class TimeColumnsInfoType:
    time_at: str | None = None
    time_start: str | None = None
    time_end: str | None = None
    cursor_column: str | None = None
    observed_at_injected: bool = False


@strawberry.type
class QualityCheckType:
    check_type: str
    status: str
    message: str = ""
    value: str | None = None
    checked_at: str = ""


@strawberry.type
class FreshnessInfoType:
    last_refreshed: str | None = None
    sla_minutes: int | None = None
    is_stale: bool = False


@strawberry.type
class QualityInfoType:
    expected_row_count_min: int | None = None
    expected_row_count_max: int | None = None
    actual_row_count: int | None = None
    latest_checks: list[QualityCheckType]


@strawberry.type
class DataResourceType:
    id: str
    schema_name: str
    table_name: str
    display_name: str
    description: str
    plugin_kind: str
    plugin_name: str
    kind: str | None = None
    query_hint: str | None = None
    as_of_macro: str | None = None
    primary_key: list[str]
    columns: list[ColumnInfoType]
    time_columns: TimeColumnsInfoType
    freshness: FreshnessInfoType
    quality: QualityInfoType
    user_notes: str = ""
    tags: list[str]
    upstream: list[DataResourceRefType] | None = None
    downstream: list[DataResourceRefType] | None = None


@strawberry.input
class DataResourceAnnotationInput:
    user_notes: str | None = None
    tags: str | None = None
    description: str | None = None
    freshness_sla_minutes: int | None = None
    expected_row_count_min: int | None = None
    expected_row_count_max: int | None = None


__all__ = [
    "JSON",
    "AuthFieldType",
    "AuthFieldsType",
    "AuthResponseType",
    "ColumnInfoType",
    "ConfigEntryType",
    "DBStatusType",
    "DataResourceAnnotationInput",
    "DataResourceRefType",
    "DataResourceType",
    "FreshnessInfoType",
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
