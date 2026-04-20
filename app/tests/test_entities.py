"""Tests for the entity system (app/entities.py + LocalUser inheritance)."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import pytest

from app.entity import (
    DEFAULT_ENTITY_TYPES,
    Entity,
    EntityIndex,
    EntityRelationship,
    EntityRelationshipType,
    seed_me_entity_index,
)
from app.entity import EntityType as EntityLookupType

if TYPE_CHECKING:
    import duckdb


def test_entity_type_seeds_present(db_con: duckdb.DuckDBPyConnection) -> None:
    """Seeding runs in the conftest fixture and should populate the lookup."""
    types = EntityLookupType.all()
    names = {t.name for t in types}
    assert "human" in names
    assert "animal" in names
    assert "residence" in names
    # Every default type shows up exactly once.
    assert {t["name"] for t in DEFAULT_ENTITY_TYPES}.issubset(names)


def test_entity_relationship_type_seeds_present(db_con: duckdb.DuckDBPyConnection) -> None:
    types = EntityRelationshipType.all()
    names = {t.name for t in types}
    assert "owner_of" in names
    assert "lives_in" in names


def test_create_entity_assigns_uuid_and_id(db_con: duckdb.DuckDBPyConnection) -> None:
    """Entity.create() generates a uuid, assigns an id, and registers the index row."""
    max_ = Entity.create(name="Max", type="animal")
    assert max_.id > 0
    assert max_.uuid
    assert len(max_.uuid) == 32

    idx = EntityIndex.find(max_.uuid)
    assert idx is not None
    assert idx.db == "user"
    assert idx.table_name == "entities"
    assert idx.row_id == max_.id


def test_find_by_uuid_roundtrips(db_con: duckdb.DuckDBPyConnection) -> None:
    original = Entity.create(name="The Oakland house", type="residence")
    fetched = Entity.find_by_uuid(original.uuid)
    assert fetched is not None
    assert fetched.id == original.id
    assert fetched.name == "The Oakland house"
    assert fetched.type == "residence"


def test_delete_entity_removes_index_and_relationships(db_con: duckdb.DuckDBPyConnection) -> None:
    alice_uuid = "a" * 32  # stand in for a LocalUser uuid
    seed_me_entity_index(local_user_id=1, local_user_uuid=alice_uuid)
    max_ = Entity.create(name="Max", type="animal")
    EntityRelationship(from_uuid=alice_uuid, to_uuid=max_.uuid, type="owner_of").upsert()

    assert EntityRelationship.find(alice_uuid, max_.uuid, "owner_of") is not None

    max_.delete()

    assert Entity.find_by_uuid(max_.uuid) is None
    assert EntityIndex.find(max_.uuid) is None
    assert EntityRelationship.find(alice_uuid, max_.uuid, "owner_of") is None


def test_relationship_upsert_and_for_entity(db_con: duckdb.DuckDBPyConnection) -> None:
    alice_uuid = "b" * 32
    seed_me_entity_index(local_user_id=1, local_user_uuid=alice_uuid)
    dog = Entity.create(name="Dog", type="animal")
    house = Entity.create(name="House", type="residence")

    EntityRelationship(from_uuid=alice_uuid, to_uuid=dog.uuid, type="owner_of").upsert()
    EntityRelationship(from_uuid=alice_uuid, to_uuid=house.uuid, type="lives_in").upsert()

    edges = EntityRelationship.for_entity(alice_uuid)
    assert len(edges) == 2
    kinds = {e.type for e in edges}
    assert kinds == {"owner_of", "lives_in"}


@pytest.mark.skip(reason="Requires LocalUser-Entity inheritance (deferred)")
def test_local_user_inherits_entity_columns(db_con: duckdb.DuckDBPyConnection) -> None:
    """LocalUser should have the entity-shaped columns from Entity via Human."""
    from app.local_users import LocalUser

    user = LocalUser.create(username="alice", password="secret1234")
    assert user.uuid  # ty: ignore[unresolved-attribute]
    assert len(user.uuid) == 32  # ty: ignore[unresolved-attribute]
    assert user.type == "human"  # ty: ignore[unresolved-attribute]
    assert user.name == "alice"  # ty: ignore[unresolved-attribute]
    assert user.status == "enabled"  # ty: ignore[unresolved-attribute]

    fetched = LocalUser.get_by_id(user.id)
    assert fetched is not None
    assert fetched.uuid == user.uuid  # ty: ignore[unresolved-attribute]
    assert fetched.type == "human"  # ty: ignore[unresolved-attribute]
    assert fetched.name == "alice"  # ty: ignore[unresolved-attribute]


@pytest.mark.skip(reason="Requires LocalUser-Entity inheritance (deferred)")
def test_local_user_authenticate_returns_full_row(db_con: duckdb.DuckDBPyConnection) -> None:
    from app.local_users import LocalUser

    created = LocalUser.create(username="bob", password="hunter2222")
    assert created.uuid  # ty: ignore[unresolved-attribute]

    logged_in = LocalUser.authenticate("bob", "hunter2222")
    assert logged_in is not None
    assert logged_in.id == created.id
    assert logged_in.name == "bob"  # ty: ignore[unresolved-attribute]
    assert logged_in.type == "human"  # ty: ignore[unresolved-attribute]

    bad = LocalUser.authenticate("bob", "wrong-password")
    assert bad is None


@pytest.mark.skip(reason="Requires LocalUser-Entity inheritance (deferred)")
def test_local_user_does_not_create_entity_index_row(db_con: duckdb.DuckDBPyConnection) -> None:
    """LocalUser.create() must NOT try to write to entity_index.

    The entity_index table lives in the user DB, but LocalUser.create runs
    in the registry DB context. Any index row for the user is seeded
    per-user during _bootstrap_user_db via seed_me_entity_index.
    """
    from app.local_users import LocalUser

    user = LocalUser.create(username="carol", password="secret12345")
    # After create, no index row should exist yet for this user.
    assert EntityIndex.find(user.uuid) is None  # ty: ignore[unresolved-attribute]


@pytest.mark.skip(reason="Requires LocalUser-Entity inheritance (deferred)")
def test_seed_me_entity_index_upserts(db_con: duckdb.DuckDBPyConnection) -> None:
    from app.local_users import LocalUser

    user = LocalUser.create(username="dave", password="secret12345")
    seed_me_entity_index(user.id, user.uuid)  # ty: ignore[unresolved-attribute]

    idx = EntityIndex.find(user.uuid)  # ty: ignore[unresolved-attribute]
    assert idx is not None
    assert idx.db == "shenas"
    assert idx.table_name == "local_users"
    assert idx.row_id == user.id

    # Idempotent on re-seed.
    seed_me_entity_index(user.id, user.uuid)  # ty: ignore[unresolved-attribute]
    idx2 = EntityIndex.find(user.uuid)  # ty: ignore[unresolved-attribute]
    assert idx2 is not None
    assert idx2.row_id == user.id


@pytest.mark.skip(reason="Requires LocalUser-Entity inheritance (deferred)")
def test_current_entity_helper_returns_local_user(db_con: duckdb.DuckDBPyConnection) -> None:
    from app.entity import current_entity
    from app.local_users import LocalUser

    user = LocalUser.create(username="eve", password="secret12345")

    class _Info:
        context: ClassVar[dict[str, int]] = {"user_id": user.id}

    me = current_entity(_Info())
    assert me is not None
    assert me.id == user.id
    assert me.uuid == user.uuid  # ty: ignore[unresolved-attribute]
    assert me.name == "eve"


def test_entity_save_updates_updated_at(db_con: duckdb.DuckDBPyConnection) -> None:
    e = Entity.create(name="Bike", type="vehicle")
    assert e.updated_at is None
    e.name = "Blue bike"
    e.save()
    assert e.updated_at is not None


@pytest.mark.parametrize("type_name", ["human", "animal", "residence", "vehicle", "device"])
def test_entity_create_with_valid_type(db_con: duckdb.DuckDBPyConnection, type_name: str) -> None:
    row = Entity.create(name=f"Test {type_name}", type=type_name)
    assert row.type == type_name
    assert row.uuid


# ---------------------------------------------------------------------------
# EntityType.concrete_types -- returns only non-abstract types
# ---------------------------------------------------------------------------


class TestConcreteTypes:
    def test_returns_only_non_abstract(self, db_con: duckdb.DuckDBPyConnection) -> None:
        concrete = EntityLookupType.concrete_types()
        assert len(concrete) > 0
        for entity_type in concrete:
            assert entity_type.is_abstract is False

    def test_excludes_abstract_types(self, db_con: duckdb.DuckDBPyConnection) -> None:
        concrete_names = {t.name for t in EntityLookupType.concrete_types()}
        # These are declared abstract in DEFAULT_ENTITY_TYPES
        abstract_names = {"entity", "physical_entity", "virtual_entity", "living_entity", "place", "group", "project"}
        assert concrete_names.isdisjoint(abstract_names)

    def test_includes_known_concrete_types(self, db_con: duckdb.DuckDBPyConnection) -> None:
        concrete_names = {t.name for t in EntityLookupType.concrete_types()}
        assert "human" in concrete_names
        assert "animal" in concrete_names
        assert "residence" in concrete_names
        assert "vehicle" in concrete_names
        assert "device" in concrete_names

    def test_results_sorted_by_name(self, db_con: duckdb.DuckDBPyConnection) -> None:
        concrete = EntityLookupType.concrete_types()
        names = [t.name for t in concrete]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# EntityType.is_subtype_of -- traverses the type hierarchy
# ---------------------------------------------------------------------------


class TestIsSubtypeOf:
    def test_self_is_subtype_of_self(self, db_con: duckdb.DuckDBPyConnection) -> None:
        assert EntityLookupType.is_subtype_of("human", "human") is True

    def test_direct_child(self, db_con: duckdb.DuckDBPyConnection) -> None:
        # human -> living_entity
        assert EntityLookupType.is_subtype_of("human", "living_entity") is True

    def test_transitive_ancestor(self, db_con: duckdb.DuckDBPyConnection) -> None:
        # human -> living_entity -> physical_entity -> entity
        assert EntityLookupType.is_subtype_of("human", "physical_entity") is True
        assert EntityLookupType.is_subtype_of("human", "entity") is True

    def test_not_subtype(self, db_con: duckdb.DuckDBPyConnection) -> None:
        # human is not a subtype of vehicle
        assert EntityLookupType.is_subtype_of("human", "vehicle") is False

    def test_ancestor_is_not_subtype_of_child(self, db_con: duckdb.DuckDBPyConnection) -> None:
        # entity is not a subtype of human (reversed)
        assert EntityLookupType.is_subtype_of("entity", "human") is False

    def test_sibling_types_are_not_subtypes(self, db_con: duckdb.DuckDBPyConnection) -> None:
        # animal and human are siblings (both under living_entity)
        assert EntityLookupType.is_subtype_of("animal", "human") is False
        assert EntityLookupType.is_subtype_of("human", "animal") is False

    def test_deep_hierarchy(self, db_con: duckdb.DuckDBPyConnection) -> None:
        # car -> vehicle -> physical_entity -> entity
        assert EntityLookupType.is_subtype_of("car", "vehicle") is True
        assert EntityLookupType.is_subtype_of("car", "physical_entity") is True
        assert EntityLookupType.is_subtype_of("car", "entity") is True

    def test_unknown_type_returns_false(self, db_con: duckdb.DuckDBPyConnection) -> None:
        assert EntityLookupType.is_subtype_of("nonexistent", "entity") is False


# ---------------------------------------------------------------------------
# EntityType.ensure_wide_view -- creates the wide view
# ---------------------------------------------------------------------------


class TestEnsureWideView:
    def test_creates_view_in_duckdb(self, db_con: duckdb.DuckDBPyConnection) -> None:
        human_type = EntityLookupType.all(where="name = 'human'")[0]
        human_type.ensure_wide_view()

        # Verify the view exists and is queryable via raw SQL
        rows = db_con.execute("SELECT * FROM entities.humans_wide").fetchall()
        assert isinstance(rows, list)

    def test_view_reflects_entities(self, db_con: duckdb.DuckDBPyConnection) -> None:
        Entity.create(name="Alice", type="human")
        human_type = EntityLookupType.all(where="name = 'human'")[0]
        human_type.ensure_wide_view()

        rows = db_con.execute("SELECT name FROM entities.humans_wide").fetchall()
        names = [r[0] for r in rows]
        assert "Alice" in names

    def test_registers_in_wide_view_registry(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import get_wide_view

        human_type = EntityLookupType.all(where="name = 'human'")[0]
        human_type.ensure_wide_view()

        view_cls = get_wide_view("human")
        assert view_cls is not None

    def test_get_wide_view_raises_before_ensure(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import _wide_view_registry, get_wide_view

        # Remove any cached view for a type to test the error
        _wide_view_registry.pop("_test_missing_", None)
        with pytest.raises(KeyError, match="No wide view"):
            get_wide_view("_test_missing_")

    def test_idempotent(self, db_con: duckdb.DuckDBPyConnection) -> None:
        human_type = EntityLookupType.all(where="name = 'human'")[0]
        # Calling twice should not raise
        human_type.ensure_wide_view()
        human_type.ensure_wide_view()


# ---------------------------------------------------------------------------
# compute_entity_id -- deterministic UUID generation
# ---------------------------------------------------------------------------


class TestComputeEntityId:
    def test_deterministic(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import compute_entity_id

        result1 = compute_entity_id("human", ["alice"])
        result2 = compute_entity_id("human", ["alice"])
        assert result1 == result2

    def test_different_type_different_id(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import compute_entity_id

        id_human = compute_entity_id("human", ["alice"])
        id_animal = compute_entity_id("animal", ["alice"])
        assert id_human != id_animal

    def test_different_pk_different_id(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import compute_entity_id

        id1 = compute_entity_id("human", ["alice"])
        id2 = compute_entity_id("human", ["bob"])
        assert id1 != id2

    def test_returns_32_char_hex(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import compute_entity_id

        result = compute_entity_id("device", ["phone-1"])
        assert len(result) == 32
        # Should be valid hex
        int(result, 16)

    def test_composite_pk(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import compute_entity_id

        result = compute_entity_id("city", ["US", "San Francisco"])
        assert len(result) == 32
        # Different order gives different id
        result2 = compute_entity_id("city", ["San Francisco", "US"])
        assert result != result2


# ---------------------------------------------------------------------------
# Entity.create -- factory method
# ---------------------------------------------------------------------------


class TestEntityCreate:
    def test_assigns_uuid(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity = Entity.create(name="Test", type="device")
        assert entity.uuid
        assert len(entity.uuid) == 32

    def test_assigns_sequential_id(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity1 = Entity.create(name="First", type="device")
        entity2 = Entity.create(name="Second", type="device")
        assert entity2.id > entity1.id

    def test_default_status_is_enabled(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity = Entity.create(name="Test", type="animal")
        assert entity.status == "enabled"

    def test_custom_description(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity = Entity.create(name="Buddy", type="animal", description="A friendly dog")
        assert entity.description == "A friendly dog"

    def test_registers_in_entity_index(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity = Entity.create(name="Indexed", type="vehicle")
        idx = EntityIndex.find(entity.uuid)
        assert idx is not None
        assert idx.db == "user"
        assert idx.table_name == "entities"
        assert idx.row_id == entity.id
        assert idx.status == "enabled"


# ---------------------------------------------------------------------------
# Entity.delete -- removes entity, index, and relationships
# ---------------------------------------------------------------------------


class TestEntityDelete:
    def test_removes_entity_row(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity = Entity.create(name="ToDelete", type="device")
        entity_uuid = entity.uuid
        entity.delete()
        assert Entity.find_by_uuid(entity_uuid) is None

    def test_removes_entity_index(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity = Entity.create(name="ToDelete", type="device")
        entity_uuid = entity.uuid
        entity.delete()
        assert EntityIndex.find(entity_uuid) is None

    def test_removes_relationships_from(self, db_con: duckdb.DuckDBPyConnection) -> None:
        source = Entity.create(name="Source", type="human")
        target = Entity.create(name="Target", type="device")
        EntityRelationship(from_uuid=source.uuid, to_uuid=target.uuid, type="owner_of").upsert()

        source.delete()
        assert EntityRelationship.find(source.uuid, target.uuid, "owner_of") is None

    def test_removes_relationships_to(self, db_con: duckdb.DuckDBPyConnection) -> None:
        source = Entity.create(name="Source", type="human")
        target = Entity.create(name="Target", type="device")
        EntityRelationship(from_uuid=source.uuid, to_uuid=target.uuid, type="owner_of").upsert()

        target.delete()
        assert EntityRelationship.find(source.uuid, target.uuid, "owner_of") is None


# ---------------------------------------------------------------------------
# seed_entity_types -- idempotent seeding
# ---------------------------------------------------------------------------


class TestSeedEntityTypes:
    def test_idempotent(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import seed_entity_types

        count_before = len(EntityLookupType.all())
        seed_entity_types()
        count_after = len(EntityLookupType.all())
        assert count_before == count_after

    def test_all_default_types_present(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import DEFAULT_ENTITY_TYPES

        all_names = {t.name for t in EntityLookupType.all()}
        for entry in DEFAULT_ENTITY_TYPES:
            assert entry["name"] in all_names

    def test_parent_relationships_set(self, db_con: duckdb.DuckDBPyConnection) -> None:
        human = EntityLookupType.all(where="name = 'human'")[0]
        assert human.parent == "living_entity"

    def test_abstract_flag_set(self, db_con: duckdb.DuckDBPyConnection) -> None:
        entity_root = EntityLookupType.all(where="name = 'entity'")[0]
        assert entity_root.is_abstract is True
        human = EntityLookupType.all(where="name = 'human'")[0]
        assert human.is_abstract is False


# ---------------------------------------------------------------------------
# seed_relationship_types -- idempotent seeding
# ---------------------------------------------------------------------------


class TestSeedRelationshipTypes:
    def test_idempotent(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import seed_relationship_types

        count_before = len(EntityRelationshipType.all())
        seed_relationship_types()
        count_after = len(EntityRelationshipType.all())
        assert count_before == count_after

    def test_all_default_relationship_types_present(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entity import DEFAULT_RELATIONSHIP_TYPES

        all_names = {t.name for t in EntityRelationshipType.all()}
        for entry in DEFAULT_RELATIONSHIP_TYPES:
            assert entry["name"] in all_names

    def test_inverse_names_set(self, db_con: duckdb.DuckDBPyConnection) -> None:
        owner = EntityRelationshipType.all(where="name = 'owner_of'")[0]
        assert owner.inverse_name == "owned by"

    def test_symmetric_flag(self, db_con: duckdb.DuckDBPyConnection) -> None:
        sibling = EntityRelationshipType.all(where="name = 'sibling_of'")[0]
        assert sibling.is_symmetric is True
        owner = EntityRelationshipType.all(where="name = 'owner_of'")[0]
        assert owner.is_symmetric is False

    def test_domain_and_range_types(self, db_con: duckdb.DuckDBPyConnection) -> None:
        owner = EntityRelationshipType.all(where="name = 'owner_of'")[0]
        assert "human" in owner.domain_types
        assert "vehicle" in owner.range_types


# ---------------------------------------------------------------------------
# seed_properties -- idempotent seeding
# ---------------------------------------------------------------------------


class TestSeedProperties:
    def test_idempotent(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entities.properties import Property
        from app.entity import seed_properties

        count_before = len(Property.all())
        seed_properties()
        count_after = len(Property.all())
        assert count_before == count_after

    def test_seeds_wikidata_properties(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entities.properties import Property

        all_props = Property.all()
        pids = {p.id for p in all_props}
        # P21 (sex or gender) should be seeded for human
        assert "P21" in pids

    def test_domain_type_assigned(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entities.properties import Property

        # P106 (occupation) is declared only for human
        p106_list = Property.all(where="id = 'P106'")
        assert len(p106_list) > 0
        domains = {p.domain_type for p in p106_list}
        assert "human" in domains

    def test_source_is_wikidata(self, db_con: duckdb.DuckDBPyConnection) -> None:
        from app.entities.properties import Property

        props = Property.all(where="source = 'wikidata'")
        assert len(props) > 0
