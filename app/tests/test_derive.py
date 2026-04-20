"""Tests for app.graphql.derive -- gql_type_from_table and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional, get_args

from app.graphql.derive import _get_field_meta, _resolve_python_type, gql_type_from_table
from app.relation import Field


@dataclass
class FakeTable:
    class _Meta:
        name = "fake"
        display_name = "Fake"
        description = "A fake table for testing"
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Primary key")] = 0
    name: Annotated[str, Field(db_type="VARCHAR", description="Name")] = ""
    score: Annotated[float, Field(db_type="DOUBLE", description="Score")] = 0.0
    enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Enabled")] | None = None


@dataclass
class TableWithDltFields:
    class _Meta:
        name = "dlt_test"
        display_name = "DLT Test"
        description = "Table with internal dlt fields"
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="ID")] = 0
    value: Annotated[str, Field(db_type="VARCHAR", description="Value")] = ""
    _dlt_valid_from: str | None = None
    _dlt_valid_to: str | None = None
    _dlt_id: str | None = None
    _dlt_load_id: str | None = None


class TestBasicDerivation:
    """Test basic type derivation from a Table class."""

    def test_returns_strawberry_type(self):
        gql_type = gql_type_from_table(FakeTable)
        # Strawberry types have __strawberry_definition__
        assert hasattr(gql_type, "__strawberry_definition__")

    def test_field_names(self):
        gql_type = gql_type_from_table(FakeTable)
        definition = gql_type.__strawberry_definition__
        field_names = {f.name for f in definition.fields}
        assert "id" in field_names
        assert "name" in field_names
        assert "score" in field_names
        assert "enabled" in field_names

    def test_field_types(self):
        gql_type = gql_type_from_table(FakeTable)
        annotations = gql_type.__annotations__
        assert annotations["id"] is int
        assert annotations["name"] is str
        assert annotations["score"] is float

    def test_uses_meta_description(self):
        gql_type = gql_type_from_table(FakeTable)
        definition = gql_type.__strawberry_definition__
        assert definition.description == "A fake table for testing"

    def test_custom_name(self):
        gql_type = gql_type_from_table(FakeTable, name="CustomName")
        assert gql_type.__name__ == "CustomName"


class TestExclude:
    """Test that the exclude parameter removes fields."""

    def test_exclude_single_field(self):
        gql_type = gql_type_from_table(FakeTable, exclude={"id"})
        definition = gql_type.__strawberry_definition__
        field_names = {f.name for f in definition.fields}
        assert "id" not in field_names
        assert "name" in field_names
        assert "score" in field_names

    def test_exclude_multiple_fields(self):
        gql_type = gql_type_from_table(FakeTable, exclude={"id", "score"})
        definition = gql_type.__strawberry_definition__
        field_names = {f.name for f in definition.fields}
        assert "id" not in field_names
        assert "score" not in field_names
        assert "name" in field_names
        assert "enabled" in field_names


class TestOverridesDefault:
    """Test overrides with a plain default value."""

    def test_override_adds_plain_field(self):
        gql_type = gql_type_from_table(
            FakeTable,
            overrides={"extra": (str, "default_value")},
        )
        definition = gql_type.__strawberry_definition__
        field_names = {f.name for f in definition.fields}
        assert "extra" in field_names

    def test_override_replaces_existing_field(self):
        gql_type = gql_type_from_table(
            FakeTable,
            overrides={"name": (int, 42)},
        )
        annotations = gql_type.__annotations__
        assert annotations["name"] is int


class TestOverridesResolver:
    """Test overrides with a callable (resolver)."""

    def test_override_with_resolver(self):
        def resolve_computed(self) -> str:
            return "computed"

        gql_type = gql_type_from_table(
            FakeTable,
            overrides={"computed": (str, resolve_computed)},
        )
        definition = gql_type.__strawberry_definition__
        field_names = {f.name for f in definition.fields}
        assert "computed" in field_names


class TestOptionalAnnotatedBool:
    """Test that Optional[Annotated[bool, Field(...)]] resolves to bool | None."""

    def test_optional_bool_type(self):
        gql_type = gql_type_from_table(FakeTable)
        annotations = gql_type.__annotations__
        enabled_type = annotations["enabled"]
        # Should be bool | None (UnionType), not str or anything else
        origin_args = get_args(enabled_type)
        assert bool in origin_args
        assert type(None) in origin_args

    def test_resolve_python_type_optional_annotated_bool(self):
        hint = Optional[Annotated[bool, Field(db_type="BOOLEAN", description="flag")]]  # noqa: UP045
        field_meta = Field(db_type="BOOLEAN", description="flag")
        result = _resolve_python_type(hint, field_meta)
        args = get_args(result)
        assert bool in args
        assert type(None) in args


class TestGetFieldMeta:
    """Test _get_field_meta extracts Field from Annotated hints."""

    def test_annotated_with_field(self):
        hint = Annotated[int, Field(db_type="INTEGER", description="test")]
        result = _get_field_meta(hint)
        assert isinstance(result, Field)
        assert result.db_type == "INTEGER"
        assert result.description == "test"

    def test_optional_annotated_with_field(self):
        hint = Optional[Annotated[bool, Field(db_type="BOOLEAN", description="flag")]]  # noqa: UP045
        result = _get_field_meta(hint)
        assert isinstance(result, Field)
        assert result.db_type == "BOOLEAN"
        assert result.description == "flag"

    def test_plain_type_returns_none(self):
        result = _get_field_meta(int)
        assert result is None

    def test_annotated_without_field_returns_none(self):
        hint = Annotated[int, "not a Field"]
        result = _get_field_meta(hint)
        assert result is None


class TestDltFieldsExcluded:
    """Test that internal dlt fields are always excluded."""

    def test_dlt_fields_not_in_output(self):
        gql_type = gql_type_from_table(TableWithDltFields)
        definition = gql_type.__strawberry_definition__
        field_names = {f.name for f in definition.fields}
        assert "_dlt_valid_from" not in field_names
        assert "_dlt_valid_to" not in field_names
        assert "_dlt_id" not in field_names
        assert "_dlt_load_id" not in field_names
        # Regular fields should still be present
        assert "id" in field_names
        assert "value" in field_names

    def test_dlt_fields_excluded_without_explicit_exclude(self):
        # Even without passing exclude, dlt fields are dropped
        gql_type = gql_type_from_table(TableWithDltFields, exclude=set())
        definition = gql_type.__strawberry_definition__
        field_names = {f.name for f in definition.fields}
        assert "_dlt_valid_from" not in field_names
        assert "_dlt_valid_to" not in field_names
