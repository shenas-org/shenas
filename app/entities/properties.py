"""Property registry: the predicate half of the statement graph.

Every attribute we record about an entity -- whether sourced from Wikidata
(``P27`` country of citizenship), projected from a source plugin
(``github:stars``), or added by the user via the UI (``user:nickname``) --
is declared once in :class:`Property`. Statements reference the property
by ``id``.

This makes the graph uniform: UI-added properties and built-in ones sit in
the same table, typed by ``datatype``. Wikidata enrichment latches onto
user-defined properties via the optional ``wikidata_pid`` mapping.
"""

from __future__ import annotations

from typing import Annotated

from app.table import Field
from shenas_sources.core.table import DimensionTable


class Property(DimensionTable):
    """A declared property that statements can use as their predicate.

    SCD2 so relabeling or datatype changes produce a history trail.
    """

    class _Meta:
        name = "properties"
        display_name = "Properties"
        description = "Registry of property predicates used by entities.statements."
        schema = "entities"
        pk = ("id",)

    id: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description=(
                "Stable property id. 'P27' etc. for Wikidata; "
                "'<plugin>:<slug>' for source-plugin properties; "
                "'user:<slug>' for UI-created properties."
            ),
            display_name="ID",
        ),
    ] = ""
    label: Annotated[
        str,
        Field(db_type="VARCHAR", description="Human-readable label.", display_name="Label"),
    ] = ""
    datatype: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description=(
                "One of: entity | string | date | number | url | coordinate | "
                "monolingualtext | boolean. Drives UI rendering and the value "
                "column in entities.statements."
            ),
            db_default="'string'",
        ),
    ] = "string"
    domain_type: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description=(
                "EntityType.name this property applies to (e.g. 'human'). NULL means it can be used on any entity type."
            ),
        ),
    ] = None
    source: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Provenance: 'wikidata' | 'user' | plugin name.",
            db_default="'user'",
        ),
    ] = "user"
    wikidata_pid: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description=(
                "Wikidata P-id this property mirrors, if any. Set on both "
                "wikidata-sourced and user-created properties that want to "
                "pick up Wikidata enrichment."
            ),
            display_name="Wikidata PID",
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Free-text description."),
    ] = None


__all__ = ["Property"]
