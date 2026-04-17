"""Tests for compute_entity_id and EntityType.default()."""

from __future__ import annotations

import pytest

from app.entity import EntityType, compute_entity_id


def test_compute_entity_id_is_deterministic() -> None:
    """Same inputs must produce the same UUID."""
    a = compute_entity_id("repository", (12345,))
    b = compute_entity_id("repository", (12345,))
    assert a == b
    # 32 hex chars (no dashes, lowercase)
    assert len(a) == 32
    assert a.lower() == a


def test_compute_entity_id_distinguishes_types_and_keys() -> None:
    """Different entity-types or PKs give different UUIDs."""
    assert compute_entity_id("repository", (1,)) != compute_entity_id("user", (1,))
    assert compute_entity_id("repository", (1,)) != compute_entity_id("repository", (2,))


def test_compute_entity_id_composite_pk() -> None:
    """Composite PKs produce a single deterministic UUID."""
    a = compute_entity_id("calendar_event", ("cal1", "event42"))
    b = compute_entity_id("calendar_event", ("cal1", "event42"))
    assert a == b
    assert a != compute_entity_id("calendar_event", ("cal1", "event43"))


def test_entity_type_default_returns_instance() -> None:
    """EntityType.default('human') returns a populated EntityType."""
    human = EntityType.default("human")
    assert human.name == "human"
    assert human.display_name == "Human"
    assert human.is_abstract is False
    assert human.parent == "living_entity"


def test_entity_type_default_unknown_raises() -> None:
    with pytest.raises(KeyError):
        EntityType.default("not_a_real_type")


def test_entity_type_default_caches() -> None:
    """Successive calls return the same instance."""
    assert EntityType.default("human") is EntityType.default("human")
