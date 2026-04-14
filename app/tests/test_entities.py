"""Tests for the entity system (app/entities.py + LocalUser inheritance)."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import pytest

from app.entities import (
    DEFAULT_ENTITY_TYPES,
    Entity,
    EntityIndex,
    EntityRelationship,
    EntityRelationshipType,
    Human,
    seed_me_entity_index,
)
from app.entities import EntityType as EntityLookupType

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
    seed_me_entity_index(db_con, local_user_id=1, local_user_uuid=alice_uuid)
    max_ = Entity.create(name="Max", type="animal")
    EntityRelationship(from_uuid=alice_uuid, to_uuid=max_.uuid, type="owner_of").upsert()

    assert EntityRelationship.find(alice_uuid, max_.uuid, "owner_of") is not None

    max_.delete()

    assert Entity.find_by_uuid(max_.uuid) is None
    assert EntityIndex.find(max_.uuid) is None
    assert EntityRelationship.find(alice_uuid, max_.uuid, "owner_of") is None


def test_relationship_upsert_and_for_entity(db_con: duckdb.DuckDBPyConnection) -> None:
    alice_uuid = "b" * 32
    seed_me_entity_index(db_con, local_user_id=1, local_user_uuid=alice_uuid)
    dog = Entity.create(name="Dog", type="animal")
    house = Entity.create(name="House", type="residence")

    EntityRelationship(from_uuid=alice_uuid, to_uuid=dog.uuid, type="owner_of").upsert()
    EntityRelationship(from_uuid=alice_uuid, to_uuid=house.uuid, type="lives_in").upsert()

    edges = EntityRelationship.for_entity(alice_uuid)
    assert len(edges) == 2
    kinds = {e.type for e in edges}
    assert kinds == {"owner_of", "lives_in"}


def test_human_is_abstract_python_class() -> None:
    """Human does not own a DuckDB table; it exists only as a Python marker."""
    assert Human._abstract is True
    # No concrete _Meta override -- Human inherits Entity's, but the bootstrap
    # walk skips abstract classes so no duplicate table is created.
    assert Human._Meta.name == Entity._Meta.name


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
    seed_me_entity_index(db_con, user.id, user.uuid)  # ty: ignore[unresolved-attribute]

    idx = EntityIndex.find(user.uuid)  # ty: ignore[unresolved-attribute]
    assert idx is not None
    assert idx.db == "shenas"
    assert idx.table_name == "local_users"
    assert idx.row_id == user.id

    # Idempotent on re-seed.
    seed_me_entity_index(db_con, user.id, user.uuid)  # ty: ignore[unresolved-attribute]
    idx2 = EntityIndex.find(user.uuid)  # ty: ignore[unresolved-attribute]
    assert idx2 is not None
    assert idx2.row_id == user.id


@pytest.mark.skip(reason="Requires LocalUser-Entity inheritance (deferred)")
def test_current_entity_helper_returns_local_user(db_con: duckdb.DuckDBPyConnection) -> None:
    from app.entities import current_entity
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
