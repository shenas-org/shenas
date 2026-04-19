"""Strawberry GraphQL types -- wraps existing Pydantic models."""

from __future__ import annotations

import contextlib

import strawberry
from strawberry.scalars import JSON

from app.models import (
    AuthField,
    AuthFieldsResponse,
    AuthResponse,
    ConfigEntry,
    InstallResponse,
    InstallResult,
    OkResponse,
    PluginInfo,
    RemoveResponse,
    ScheduleInfo,
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
    source: DataResourceType
    target: DataResourceType
    source_plugin: str
    params: str
    description: str
    is_default: bool
    enabled: bool
    added_at: str | None
    updated_at: str | None
    status_changed_at: str | None

    @strawberry.field
    def transform_type_display_name(self) -> str:
        from app.plugin import Plugin

        try:
            for cls in Plugin.load_by_kind("transformer"):
                if getattr(cls, "name", "") == self.transform_type:
                    return getattr(cls, "display_name", self.transform_type)
        except Exception:
            pass
        return self.transform_type

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


# -- Model types ---------------------------------------------------------------


@strawberry.type
class ModelInfoType:
    name: str
    display_name: str = ""
    description: str = ""
    version: str = ""
    enabled: bool = True


@strawberry.type
class ModelStatusType:
    name: str
    available: bool = False
    current_round: int | None = None


@strawberry.type
class ModelPredictionType:
    name: str
    predictions: list[float]
    labels: list[str]


# -- Dashboard + Dependency types -----------------------------------------------


@strawberry.type
class DashboardType:
    name: str
    display_name: str
    tag: str = ""
    js: str = ""
    description: str = ""


@strawberry.type
class DependencyEdge:
    source: str
    targets: list[str]


# -- Hypothesis types ----------------------------------------------------------


@strawberry.type
class HypothesisType:
    id: int
    question: str
    plan: str | None = None
    recipe_json: str = ""
    inputs: str | None = None
    result_json: str | None = None
    interpretation: str | None = None
    created_at: str | None = None
    model: str | None = None
    promoted_to: str | None = None
    llm_input_tokens: int | None = None
    llm_output_tokens: int | None = None
    llm_elapsed_ms: float | None = None
    query_elapsed_ms: float | None = None
    wall_clock_ms: float | None = None
    mode: str | None = None
    parent_id: int | None = None
    is_suggested: bool | None = None


@strawberry.type
class FindingType:
    id: int
    exposure: str
    outcome: str
    direction: str = ""
    effect_size: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    evidence_level: str | None = None
    sample_size: int | None = None
    mechanism: str | None = None
    citation: str = ""
    doi: str | None = None
    exposure_categories: str | None = None
    outcome_categories: str | None = None
    source_ref: str | None = None


@strawberry.type
class HypothesisSuggestionType:
    question: str
    rationale: str = ""
    datasets_involved: list[str]
    complexity: str = ""
    score: float = 0.0


# -- Transformer info types ----------------------------------------------------


@strawberry.type
class ParamFieldType:
    name: str
    label: str = ""
    type: str = "text"
    required: bool = False
    description: str = ""
    default: str | None = None
    options: list[str] | None = None


@strawberry.type
class TransformerInfoType:
    name: str
    display_name: str
    description: str = ""
    param_schema: list[ParamFieldType]


@strawberry.type
class SeedResultType:
    seeded: list[str]
    count: int


@strawberry.type
class TransformRunResultType:
    name: str
    count: int


# -- Suggestion types ----------------------------------------------------------


@strawberry.type
class SuggestedDatasetType:
    name: str
    is_suggested: bool = True
    enabled: bool = False
    table_name: str | None = None
    grain: str | None = None
    title: str | None = None


@strawberry.type
class SuggestedAnalysisType:
    id: int
    question: str
    rationale: str = ""
    datasets_involved: list[str]
    complexity: str = ""


# -- Category types ------------------------------------------------------------


@strawberry.type
class CategoryValueType:
    value: str
    sort_order: int = 0
    color: str | None = None


@strawberry.type
class CategorySetType:
    id: str
    display_name: str
    description: str = ""
    values: list[CategoryValueType]


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
    nullable: bool = True
    description: str = ""
    display_name: str = ""
    unit: str | None = None
    category: str = ""
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
class PlotHintType:
    y: str
    group_by: str | None = None
    chart_type: str = "line"
    label: str | None = None


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
    plugin: PluginInfoType
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
    upstream_transforms: list[TransformType] | None = None
    downstream_transforms: list[TransformType] | None = None


@strawberry.input
class DataResourceAnnotationInput:
    user_notes: str | None = None
    tags: str | None = None
    description: str | None = None
    freshness_sla_minutes: int | None = None
    expected_row_count_min: int | None = None
    expected_row_count_max: int | None = None


# -- Entity types --------------------------------------------------------------


@strawberry.type
class EntityTypeType:
    name: str
    display_name: str
    description: str = ""
    icon: str = ""
    parent: str | None = None
    is_abstract: bool = False
    wikidata_qid: str | None = None


@strawberry.type
class EntityRelationshipTypeType:
    name: str
    display_name: str
    description: str = ""
    inverse_name: str | None = None
    is_symmetric: bool = False
    domain_types: list[str] = strawberry.field(default_factory=list)
    range_types: list[str] = strawberry.field(default_factory=list)
    wikidata_pid: str | None = None


@strawberry.type
class GqlEntityType:
    uuid: str
    type: str
    name: str
    description: str = ""
    status: str = "enabled"
    added_at: str | None = None
    updated_at: str | None = None
    is_me: bool = False

    @strawberry.field
    def statements(self) -> list[StatementType]:
        """Current statements for this entity, joined with property metadata."""
        import json as _json

        from app.entities.properties import Property
        from app.entities.statements import Statement

        stmts = Statement.all(
            where="entity_id = ?",
            params=[self.uuid],
            order_by="property_id, value",
        )
        pids = {s.property_id for s in stmts}
        props_by_id: dict[str, Property] = {}
        for pid in pids:
            p = Property.all(
                where="id = ?",
                params=[pid],
                limit=1,
            )
            if p:
                props_by_id[pid] = p[0]

        out: list[StatementType] = []
        for s in stmts:
            parsed_q: JSON | None = None
            if isinstance(s.qualifiers, str) and s.qualifiers:
                with contextlib.suppress(_json.JSONDecodeError):
                    parsed_q = _json.loads(s.qualifiers)
            prop = props_by_id.get(s.property_id)
            out.append(
                StatementType(
                    entity_id=s.entity_id,
                    property_id=s.property_id,
                    value=s.value,
                    value_label=s.value_label,
                    rank=s.rank or "normal",
                    qualifiers=parsed_q,
                    source=s.source or "user",
                    property_label=prop.label if prop else None,
                    datatype=prop.datatype if prop else None,
                )
            )
        return out


@strawberry.type
class GqlEntityRelationshipType:
    from_uuid: str
    to_uuid: str
    type: str
    description: str = ""
    added_at: str | None = None
    updated_at: str | None = None


@strawberry.input
class EntityCreateInput:
    name: str
    type: str = "human"
    description: str = ""
    status: str = "enabled"


@strawberry.input
class EntityUpdateInput:
    name: str | None = None
    type: str | None = None
    description: str | None = None
    status: str | None = None


# -- Statement / Property graph -----------------------------------------------


@strawberry.type
class PropertyType:
    """A predicate in entities.properties (registry of statement predicates)."""

    id: str
    label: str
    datatype: str = "string"
    domain_type: str | None = None
    source: str = "user"
    wikidata_pid: str | None = None
    description: str | None = None


@strawberry.type
class StatementType:
    """A single (entity, property, value) triple from entities.statements."""

    entity_id: str
    property_id: str
    value: str
    value_label: str | None = None
    rank: str = "normal"
    qualifiers: JSON | None = None
    source: str = "user"
    # Resolved property fields (joined from entities.properties for convenience).
    property_label: str | None = None
    datatype: str | None = None


@strawberry.input
class PropertyCreateInput:
    label: str
    datatype: str = "string"
    domain_type: str | None = None
    wikidata_pid: str | None = None
    description: str | None = None
    # If omitted, the resolver derives ``user:<slug(label)>``.
    id: str | None = None


@strawberry.input
class StatementUpsertInput:
    entity_id: str
    property_id: str
    value: str
    value_label: str | None = None
    rank: str = "normal"
    qualifiers: JSON | None = None


__all__ = [
    "JSON",
    "AuthFieldType",
    "AuthFieldsType",
    "AuthResponseType",
    "ColumnInfoType",
    "ConfigEntryType",
    "DataResourceAnnotationInput",
    "DataResourceRefType",
    "DataResourceType",
    "EntityCreateInput",
    "EntityRelationshipTypeType",
    "EntityTypeType",
    "EntityUpdateInput",
    "FreshnessInfoType",
    "GqlEntityRelationshipType",
    "GqlEntityType",
    "InstallResponseType",
    "InstallResultType",
    "OkType",
    "PlotHintType",
    "PluginInfoType",
    "PropertyCreateInput",
    "PropertyType",
    "RemoveResponseType",
    "ScheduleInfoType",
    "StatementType",
    "StatementUpsertInput",
    "TableEntry",
    "ThemeInfo",
    "TransformCreateInput",
    "TransformType",
]
