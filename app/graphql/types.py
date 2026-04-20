"""Strawberry GraphQL types.

Organised into four sections:

1. **Pydantic-wrapped**: auto-generated from ``app.models`` Pydantic classes.
2. **Table-derived**: auto-generated from ``Table`` subclasses via ``gql_type_from_table``.
3. **Hand-written output types**: view-model types that don't map 1:1 to a model.
4. **Input types**: mutation input arguments.
"""

from __future__ import annotations

import contextlib
from typing import Any

import strawberry
from strawberry.scalars import JSON

from app.graphql.derive import gql_type_from_table as _derive
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

# ============================================================================
# 1. Pydantic-wrapped types
# ============================================================================

_PYDANTIC_TYPES: list[dict[str, Any]] = [
    {"model": OkResponse, "name": "OkType"},
    {"model": AuthField, "name": "AuthFieldType"},
    {"model": AuthFieldsResponse, "name": "AuthFieldsType"},
    {"model": AuthResponse, "name": "AuthResponseType"},
    {"model": ConfigEntry, "name": "ConfigEntryType"},
    {"model": PluginInfo, "name": "PluginInfoType"},
    {"model": InstallResult, "name": "InstallResultType"},
    {"model": InstallResponse, "name": "InstallResponseType"},
    {"model": RemoveResponse, "name": "RemoveResponseType"},
    {"model": ScheduleInfo, "name": "ScheduleInfoType"},
]

for _pydantic_cfg in _PYDANTIC_TYPES:
    _pydantic_cls = type(_pydantic_cfg["name"], (), {})
    _pydantic_cls = strawberry.experimental.pydantic.type(model=_pydantic_cfg["model"], all_fields=True)(_pydantic_cls)
    globals()[_pydantic_cfg["name"]] = _pydantic_cls

OkType = globals()["OkType"]
AuthFieldType = globals()["AuthFieldType"]
AuthFieldsType = globals()["AuthFieldsType"]
AuthResponseType = globals()["AuthResponseType"]
ConfigEntryType = globals()["ConfigEntryType"]
PluginInfoType = globals()["PluginInfoType"]
InstallResultType = globals()["InstallResultType"]
InstallResponseType = globals()["InstallResponseType"]
RemoveResponseType = globals()["RemoveResponseType"]
ScheduleInfoType = globals()["ScheduleInfoType"]


# ============================================================================
# 2. Hand-written output types (view models, no 1:1 model mapping)
# ============================================================================

# -- Misc --------------------------------------------------------------------


@strawberry.type
class TableEntry:
    schema_name: str = strawberry.field(name="schema")
    table: str


@strawberry.type
class ThemeInfo:
    name: str | None
    css: str | None


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


# -- Data catalog ------------------------------------------------------------


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


# DataResourceType is defined after the derive section (it references TransformType).

# -- Models ------------------------------------------------------------------


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


# -- Transformers ------------------------------------------------------------


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


# -- Suggestions -------------------------------------------------------------


@strawberry.type
class HypothesisSuggestionType:
    question: str
    rationale: str = ""
    datasets_involved: list[str]
    complexity: str = ""
    score: float = 0.0


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


# -- Categories --------------------------------------------------------------


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


# -- Statements / Properties -------------------------------------------------


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
    property_label: str | None = None
    datatype: str | None = None


# ============================================================================
# 3. Table-derived types (auto-generated from Table subclasses)
# ============================================================================
#
# Each entry declares:
#   cls      -- "module.path:ClassName" to import
#   name     -- GraphQL type name
#   exclude  -- fields to omit (optional)
#   overrides -- {field: (type, resolver_or_default)} for computed fields (optional)


def _sql_from_params(self: Any) -> str:
    """Extract SQL from params JSON for convenience."""
    import json

    try:
        return json.loads(self.params).get("sql", "")
    except (json.JSONDecodeError, TypeError):
        return ""


def _import_class(path: str) -> type:
    """Import a class from 'module.path:ClassName'."""
    module_path, class_name = path.rsplit(":", 1)
    return getattr(__import__(module_path, fromlist=[class_name]), class_name)


# NOTE: DataResourceType references TransformType, so TransformType must be
# derived before DataResourceType is defined. The list order matters.
_DERIVED_TYPES: list[dict[str, Any]] = [
    {
        "cls": "app.hypotheses:Hypothesis",
        "name": "HypothesisType",
    },
    {
        "cls": "app.finding:Finding",
        "name": "FindingType",
    },
    {
        "cls": "app.entity:EntityType",
        "name": "EntityTypeType",
        "exclude": {"wikidata_seed", "wikidata_properties", "added_at"},
    },
    {
        "cls": "app.entity:EntityRelationshipType",
        "name": "EntityRelationshipTypeType",
        "exclude": {"added_at"},
    },
    {
        "cls": "app.entity:Entity",
        "name": "_EntityBase",
        "exclude": {"id", "status_changed_at"},
    },
    {
        "cls": "app.entity:EntityRelationship",
        "name": "GqlEntityRelationshipType",
        "exclude": {"id"},
    },
]

for _cfg in _DERIVED_TYPES:
    _type = _derive(
        _import_class(_cfg["cls"]),
        name=_cfg["name"],
        exclude=_cfg.get("exclude"),
        overrides=_cfg.get("overrides"),
    )
    globals()[_cfg["name"]] = _type

# Aliases (make names visible to static analysis / IDE imports).
HypothesisType = globals()["HypothesisType"]
FindingType = globals()["FindingType"]
EntityTypeType = globals()["EntityTypeType"]
EntityRelationshipTypeType = globals()["EntityRelationshipTypeType"]
GqlEntityRelationshipType = globals()["GqlEntityRelationshipType"]
_EntityBase = globals()["_EntityBase"]


# -- TransformType + DataResourceType have a circular reference.
# Derive TransformType base, define DataResourceType, then subclass.

_TransformBase = _derive(
    _import_class("shenas_transformers.core.transform:Transform"),
    name="_TransformBase",
    exclude={"source_data_resource_id", "target_data_resource_id", "is_suggested"},
    overrides={
        "sql": (str, _sql_from_params),
    },
)


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
    upstream_transforms: list[_TransformBase] | None = None
    downstream_transforms: list[_TransformBase] | None = None


@strawberry.type
class TransformType(_TransformBase):  # type: ignore[misc]
    """Adds resolved source/target resources to the derived Transform fields."""

    source: DataResourceType | None = None
    target: DataResourceType | None = None


# -- GqlEntityType (subclass of derived _EntityBase, has complex resolvers) --


@strawberry.type(description="A typed node in the entity graph.")
class GqlEntityType(_EntityBase):
    is_me: bool = False

    @classmethod
    def build(cls, *, is_me: bool = False, **kwargs: Any) -> GqlEntityType:
        return cls(**kwargs, is_me=is_me)

    @strawberry.field
    def sources(self) -> list[str]:
        """Distinct source plugin names that produced statements for this entity."""
        from app.entities.statements import Statement

        stmts = Statement.all(where="entity_id = ? AND source IS NOT NULL", params=[self.uuid])
        return sorted({s.source for s in stmts if s.source})

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
            p = Property.all(where="id = ?", params=[pid], limit=1)
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


# ============================================================================
# 4. Input types
# ============================================================================


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


@strawberry.input
class DataResourceAnnotationInput:
    user_notes: str | None = None
    tags: str | None = None
    description: str | None = None
    freshness_sla_minutes: int | None = None
    expected_row_count_min: int | None = None
    expected_row_count_max: int | None = None


@strawberry.input
class EntityTypeCreateInput:
    display_name: str
    parent: str | None = None
    description: str = ""
    icon: str = ""


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


@strawberry.input
class PropertyCreateInput:
    label: str
    datatype: str = "string"
    domain_type: str | None = None
    wikidata_pid: str | None = None
    description: str | None = None
    id: str | None = None


@strawberry.input
class StatementUpsertInput:
    entity_id: str
    property_id: str
    value: str
    value_label: str | None = None
    rank: str = "normal"
    qualifiers: JSON | None = None


# ============================================================================
# __all__
# ============================================================================

__all__ = [
    "JSON",
    "AuthFieldType",
    "AuthFieldsType",
    "AuthResponseType",
    "CategorySetType",
    "CategoryValueType",
    "ColumnInfoType",
    "ConfigEntryType",
    "DashboardType",
    "DataResourceAnnotationInput",
    "DataResourceRefType",
    "DataResourceType",
    "DependencyEdge",
    "EntityCreateInput",
    "EntityRelationshipTypeType",
    "EntityTypeCreateInput",
    "EntityTypeType",
    "EntityUpdateInput",
    "FindingType",
    "FreshnessInfoType",
    "GqlEntityRelationshipType",
    "GqlEntityType",
    "HypothesisSuggestionType",
    "HypothesisType",
    "InstallResponseType",
    "InstallResultType",
    "ModelInfoType",
    "ModelPredictionType",
    "ModelStatusType",
    "OkType",
    "ParamFieldType",
    "PlotHintType",
    "PluginInfoType",
    "PropertyCreateInput",
    "PropertyType",
    "QualityCheckType",
    "QualityInfoType",
    "RemoveResponseType",
    "ScheduleInfoType",
    "SeedResultType",
    "StatementType",
    "StatementUpsertInput",
    "SuggestedAnalysisType",
    "SuggestedDatasetType",
    "TableEntry",
    "ThemeInfo",
    "TimeColumnsInfoType",
    "TransformCreateInput",
    "TransformRunResultType",
    "TransformType",
    "TransformerInfoType",
]
