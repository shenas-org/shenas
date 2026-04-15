"""Statement table: the (entity, property, value) triple store.

Every attribute of every entity lives here -- Wikidata-sourced, projected
from raw source tables, or entered by the user. This is the uniform graph
layer: one index seek resolves ``(entity_id, property_id) -> value``, and
one reverse index resolves ``(value, property_id) -> entity_id`` for
graph traversal.

Typed per-type wide views (``entities.<type>s_wide``) pivot statements for
dashboard-style browsing; see :meth:`app.entity.EntityType.ensure_wide_view`.
"""

from __future__ import annotations

from typing import Annotated

from app.table import Field
from shenas_sources.core.table import DimensionTable


class Statement(DimensionTable):
    """One (entity, property, value) triple. SCD2 closes stale slices.

    ``value`` holds a QID / entity_id when the referenced :class:`Property`
    has ``datatype='entity'``, otherwise a literal rendered as text.
    ``value_label`` is an optional pre-rendered human-readable form used by
    wide views to avoid a second lookup.

    Qualifiers (Wikidata-style rank-refining context, e.g. ``P580`` start
    date / ``P582`` end date) live in a JSON blob read as a bag -- the hot
    qualifier PIDs can be promoted to their own columns in a follow-up.
    """

    class _Meta:
        name = "statements"
        display_name = "Statements"
        description = "Entity attribute triples: (entity_id, property_id, value)."
        schema = "entities"
        pk = ("entity_id", "property_id", "value")

    entity_id: Annotated[
        str,
        Field(db_type="VARCHAR", description="Subject: entity_id in entities.entities.", display_name="Entity ID"),
    ] = ""
    property_id: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Predicate: entities.properties.id (P27, github:stars, user:nickname, ...).",
            display_name="Property",
        ),
    ] = ""
    value: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description=(
                "Object: QID / entity_id if the property is entity-typed, else the literal value serialised as text."
            ),
            display_name="Value",
        ),
    ] = ""
    value_label: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description=(
                "Pre-rendered human-readable form (label for entity values, formatted literal otherwise). Used by wide views."
            ),
            display_name="Label",
        ),
    ] = None
    rank: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Wikidata-style rank: preferred | normal | deprecated.",
            db_default="'normal'",
        ),
    ] = "normal"
    qualifiers: Annotated[
        str | None,
        Field(
            db_type="JSON",
            description=(
                "Map of qualifier property_id -> value(s) as JSON. Read as a bag; not indexed for predicate filtering."
            ),
        ),
    ] = None
    source: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Provenance: 'wikidata' | 'user' | plugin name. Mirrors Property.source.",
            db_default="'user'",
        ),
    ] = "user"


__all__ = ["Statement"]
