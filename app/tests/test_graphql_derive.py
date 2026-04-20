"""Tests for the GraphQL type derivation from Table subclasses."""

import dataclasses
from typing import Annotated

from app.graphql.derive import (
    _get_field_meta,
    _resolve_python_type,
    gql_type_from_table,
)
from app.relation import Field

# -- Helpers: minimal Table-like dataclass for testing -----------------------


@dataclasses.dataclass
class _FakeTable:
    class _Meta:
        description = "A test table"

    name: Annotated[str, Field(db_type="VARCHAR", description="Name")] = ""
    count: Annotated[int, Field(db_type="INTEGER", description="Count")] = 0
    score: Annotated[float | None, Field(db_type="DOUBLE", description="Score")] = None
    active: Annotated[bool, Field(db_type="BOOLEAN", description="Active")] = True
    _internal: str = ""  # should be excluded (leading _)


# -- _resolve_python_type ---------------------------------------------------


class TestResolvePythonType:
    def test_varchar_maps_to_str(self):
        hint = Annotated[str, Field(db_type="VARCHAR", description="test")]
        meta = _get_field_meta(hint)
        assert _resolve_python_type(hint, meta) is str

    def test_integer_maps_to_int(self):
        hint = Annotated[int, Field(db_type="INTEGER", description="test")]
        meta = _get_field_meta(hint)
        assert _resolve_python_type(hint, meta) is int

    def test_double_maps_to_float(self):
        hint = Annotated[float, Field(db_type="DOUBLE", description="test")]
        meta = _get_field_meta(hint)
        assert _resolve_python_type(hint, meta) is float

    def test_boolean_maps_to_bool(self):
        hint = Annotated[bool, Field(db_type="BOOLEAN", description="test")]
        meta = _get_field_meta(hint)
        assert _resolve_python_type(hint, meta) is bool

    def test_optional_preserves_nullable(self):
        hint = Annotated[float | None, Field(db_type="DOUBLE", description="test")]
        meta = _get_field_meta(hint)
        result = _resolve_python_type(hint, meta)
        # Should be float | None
        assert type(None) in result.__args__

    def test_no_field_meta_uses_raw_type(self):
        result = _resolve_python_type(str, None)
        assert result is str

    def test_unknown_db_type_defaults_to_str(self):
        hint = Annotated[str, Field(db_type="CUSTOM_TYPE", description="test")]
        meta = _get_field_meta(hint)
        assert _resolve_python_type(hint, meta) is str


# -- _get_field_meta ---------------------------------------------------------


class TestGetFieldMeta:
    def test_extracts_field_from_annotated(self):
        hint = Annotated[str, Field(db_type="VARCHAR", description="test")]
        meta = _get_field_meta(hint)
        assert meta is not None
        assert meta.db_type == "VARCHAR"

    def test_returns_none_for_plain_type(self):
        assert _get_field_meta(str) is None
        assert _get_field_meta(int) is None

    def test_extracts_from_optional_annotated(self):
        hint = Annotated[str, Field(db_type="TEXT", description="test")] | None
        meta = _get_field_meta(hint)
        assert meta is not None
        assert meta.db_type == "TEXT"


# -- gql_type_from_table -----------------------------------------------------


class TestGqlTypeFromTable:
    def test_creates_strawberry_type(self):
        gql_type = gql_type_from_table(_FakeTable, name="TestType")
        assert hasattr(gql_type, "__strawberry_definition__")

    def test_uses_meta_description(self):
        gql_type = gql_type_from_table(_FakeTable, name="TestType")
        definition = gql_type.__strawberry_definition__
        assert definition.description == "A test table"

    def test_includes_public_fields(self):
        gql_type = gql_type_from_table(_FakeTable, name="TestType")
        field_names = {f.name for f in gql_type.__strawberry_definition__.fields}
        assert "name" in field_names
        assert "count" in field_names
        assert "score" in field_names
        assert "active" in field_names

    def test_excludes_internal_fields(self):
        gql_type = gql_type_from_table(_FakeTable, name="TestType")
        field_names = {f.name for f in gql_type.__strawberry_definition__.fields}
        assert "_internal" not in field_names
        assert "internal" not in field_names

    def test_exclude_parameter(self):
        gql_type = gql_type_from_table(_FakeTable, name="TestType", exclude={"count", "active"})
        field_names = {f.name for f in gql_type.__strawberry_definition__.fields}
        assert "name" in field_names
        assert "count" not in field_names
        assert "active" not in field_names

    def test_overrides_with_resolver(self):
        def my_resolver(self) -> str:
            return "computed"

        gql_type = gql_type_from_table(
            _FakeTable,
            name="TestType",
            overrides={"computed_field": (str, my_resolver)},
        )
        field_names = {f.name for f in gql_type.__strawberry_definition__.fields}
        assert "computed_field" in field_names

    def test_overrides_with_default_value(self):
        gql_type = gql_type_from_table(
            _FakeTable,
            name="TestType",
            overrides={"extra": (str, "default_val")},
        )
        field_names = {f.name for f in gql_type.__strawberry_definition__.fields}
        assert "extra" in field_names

    def test_overrides_replace_excluded_fields(self):
        gql_type = gql_type_from_table(
            _FakeTable,
            name="TestType",
            overrides={"name": (int, 0)},
        )
        # The override replaces the original field
        field_names = {f.name for f in gql_type.__strawberry_definition__.fields}
        assert "name" in field_names

    def test_custom_name(self):
        gql_type = gql_type_from_table(_FakeTable, name="CustomName")
        assert gql_type.__name__ == "CustomName"

    def test_default_name_from_class(self):
        gql_type = gql_type_from_table(_FakeTable)
        assert gql_type.__name__ == "_FakeTable"

    def test_instantiation_with_defaults(self):
        gql_type = gql_type_from_table(_FakeTable, name="TestType")
        instance = gql_type()
        assert instance.name == ""
        assert instance.count == 0
        assert instance.active is True
        assert instance.score is None
