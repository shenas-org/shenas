"""Wikidata source -- generic entity enrichment via statements.

Iterates every entity that carries a ``wikidata:qid`` statement (declared
by the user or by a source plugin projection), groups them by entity type,
discovers the Wikidata P-ids that each type cares about from the
EntityType's ``wikidata_properties`` list, and fetches them in batched
SPARQL calls. Every result becomes a row in ``entities.statements`` with
``source='wikidata'``. Values referencing other Wikidata items store the
QID in ``value`` and the English label in ``value_label``.

No authentication required; the SPARQL endpoint at
https://query.wikidata.org/sparql is public.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shenas_sources.core.source import Source

if TYPE_CHECKING:
    from collections.abc import Callable


class WikidataSource(Source):
    name = "wikidata"
    display_name = "Wikidata"
    # Wikidata now lands in entities.statements; the Data tab shows the
    # generic triple list filtered to source='wikidata'.
    primary_table = "entities.statements"
    description = (
        "Structured knowledge from Wikidata. Fetches every declared "
        "Wikidata property for each entity whose wikidata:qid is set, "
        "and stores the result as rows in entities.statements."
    )

    def build_client(self) -> Any:
        from shenas_sources.wikidata.client import WikidataClient

        return WikidataClient()

    def resources(self, client: Any) -> list[Any]:  # noqa: ARG002
        """No dlt-managed resources -- :meth:`sync` writes straight to statements."""
        return []

    def sync(
        self,
        *,
        full_refresh: bool = False,
        on_progress: Callable[[str, str], None] | None = None,
        **_kwargs: Any,
    ) -> None:
        from app.entity import EntityType

        client = self.build_client()
        total = 0
        try:
            # Seed entities for types with wikidata_seed=True (e.g. country, city).
            # This also fetches their properties in the same pass.
            types = {t.name: t for t in EntityType.all()}
            seeded_types: set[str] = set()
            for entity_type in types.values():
                if getattr(entity_type, "wikidata_seed", False):
                    seeded_types.add(entity_type.name)
            total += self._seed_reference_entities(client, types, on_progress)

            # Enrich remaining (non-seeded) entities that have wikidata:qid.
            groups = self._load_entity_groups()
            if not groups and total == 0:
                if on_progress:
                    on_progress("statements", "No entities with wikidata:qid found. Set a QID on an entity first.")
                self.log.info("wikidata sync: no entities with wikidata:qid; nothing to fetch")
                return

            total += self._enrich_entities(client, groups, types, seeded_types, on_progress)
        finally:
            client.close()

        # Convert entity-typed statements into EntityRelationship rows.
        relationships_created = self._create_entity_relationships(on_progress)

        if on_progress:
            on_progress("statements", f"Wrote {total} statements, {relationships_created} relationships from Wikidata.")
        self.log.info("wikidata sync: wrote %d statements, %d relationships", total, relationships_created)
        self._post_sync(full_refresh)

    # ------------------------------------------------------------------
    # Seed reference entities
    # ------------------------------------------------------------------

    def _enrich_entities(
        self,
        client: Any,
        groups: dict[str, list[tuple[str, str]]],
        types: dict[str, Any],
        skip_types: set[str],
        on_progress: Callable[[str, str], None] | None,
    ) -> int:
        """Fetch Wikidata properties for non-seeded entity types."""
        total = 0
        for type_name, pairs in groups.items():
            if type_name in skip_types or type_name not in types:
                continue
            pids = _pids_for_type(type_name)
            if not pids:
                continue
            qids = sorted({qid for _, qid in pairs})
            if on_progress:
                on_progress(type_name, f"Fetching {len(pids)} properties for {len(qids)} {type_name} entities...")
            bindings = client.fetch_statements(qids, pids)
            qid_to_entity = {qid: entity_id for entity_id, qid in pairs}
            for binding in bindings:
                entity_id = qid_to_entity.get(binding["qid"])
                if not entity_id:
                    continue
                self._upsert_property(binding["pid"], binding.get("value_type", "string"))
                self._upsert_statement(entity_id, binding)
                total += 1
        return total

    def _seed_reference_entities(
        self,
        client: Any,
        types: dict[str, Any],
        on_progress: Callable[[str, str], None] | None,
    ) -> int:
        """Seed entities for types with wikidata_seed=True and fetch their properties.

        Uses fetch_instances_with_properties to get both the entity list and
        their property values in one combined pass per type, avoiding a
        separate enrichment round-trip for seeded entities.

        Returns the total number of statements written.
        """
        from app.entities.properties import Property
        from app.entity import Entity, compute_entity_id

        if Property.find("wikidata:qid") is None:
            Property.from_row(("wikidata:qid", "Wikidata QID", "string", None, "wikidata", None, None)).insert()

        total_statements = 0
        for entity_type in types.values():
            if not getattr(entity_type, "wikidata_seed", False):
                continue
            type_qid = getattr(entity_type, "wikidata_qid", None)
            if not type_qid:
                continue

            pids = _pids_for_type(entity_type.name)
            if on_progress:
                on_progress("seed", f"Seeding {entity_type.display_name} entities + properties from Wikidata...")
            self.log.info("Seeding %s entities (Q=%s) with %d properties", entity_type.name, type_qid, len(pids))

            instances, statements = client.fetch_instances_with_properties(type_qid, pids, limit=500)

            # Create entities + wikidata:qid statements.
            created = 0
            qid_to_entity: dict[str, str] = {}
            for instance in instances:
                instance_qid = instance["qid"]
                label = instance["label"]
                entity_id = compute_entity_id(entity_type.name, (label,))
                qid_to_entity[instance_qid] = entity_id

                if Entity.find_by_uuid(entity_id) is None:
                    Entity(
                        uuid=entity_id,
                        type=entity_type.name,
                        name=label,
                        status="disabled",
                    ).insert()
                    created += 1

                # Upsert wikidata:qid statement. Use _upsert_statement to handle SCD2.
                self._upsert_statement(
                    entity_id,
                    {
                        "pid": "wikidata:qid",
                        "value": instance_qid,
                        "value_label": label,
                        "rank": "normal",
                        "value_type": "string",
                    },
                )

            # Process property statements from the same fetch.
            for binding in statements:
                entity_id = qid_to_entity.get(binding["qid"])
                if not entity_id:
                    continue
                self._upsert_property(binding["pid"], binding.get("value_type", "string"))
                self._upsert_statement(entity_id, binding)
                total_statements += 1

            self.log.info("Seeded %d new %s entities, %d statements", created, entity_type.name, total_statements)
            if on_progress:
                on_progress("seed", f"Seeded {created} new {entity_type.display_name} entities.")

        return total_statements

    # ------------------------------------------------------------------
    # Entity relationships from Wikidata statements
    # ------------------------------------------------------------------

    def _create_entity_relationships(
        self,
        on_progress: Callable[[str, str], None] | None,
    ) -> int:
        """Create EntityRelationship rows from entity-typed Wikidata statements.

        For each statement with source='wikidata' whose value is a QID
        matching a known entity's wikidata:qid, and whose property maps
        to a relationship type (via wikidata_pid), create a relationship.
        """
        from app.entities.statements import Statement
        from app.entity import EntityRelationship, EntityRelationshipType

        # Build PID -> relationship_type name mapping.
        # wikidata_pid can be comma-separated (e.g. "P276,P17" for located_in).
        pid_to_relationship: dict[str, str] = {}
        for relationship_type in EntityRelationshipType.all():
            raw_pid = getattr(relationship_type, "wikidata_pid", None) or ""
            for single_pid in raw_pid.split(","):
                stripped = single_pid.strip()
                if stripped:
                    pid_to_relationship[stripped] = relationship_type.name

        if not pid_to_relationship:
            return 0

        # Build QID -> entity_id mapping from wikidata:qid statements.
        qid_statements = Statement.all(where="property_id = 'wikidata:qid' AND value IS NOT NULL AND value <> ''")
        qid_to_entity: dict[str, str] = {statement.value: statement.entity_id for statement in qid_statements}

        # Find Wikidata statements whose PID maps to a relationship type
        # and whose value is a QID of a known entity.
        wikidata_statements = Statement.all(where="source = 'wikidata'")
        created = 0
        for statement in wikidata_statements:
            relationship_name = pid_to_relationship.get(statement.property_id)
            if not relationship_name:
                continue
            target_entity_id = qid_to_entity.get(statement.value)
            if not target_entity_id:
                continue
            if statement.entity_id == target_entity_id:
                continue

            existing = EntityRelationship.find(statement.entity_id, target_entity_id, relationship_name)
            if existing is None:
                EntityRelationship(
                    from_uuid=statement.entity_id,
                    to_uuid=target_entity_id,
                    type=relationship_name,
                ).upsert()
                created += 1

        if created and on_progress:
            on_progress("relationships", f"Created {created} entity relationships from Wikidata.")
        self.log.info("wikidata: created %d entity relationships", created)
        return created

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_entity_groups(self) -> dict[str, list[tuple[str, str]]]:
        """Return ``{entity_type: [(entity_id, wikidata_qid), ...]}``.

        Reads the current live slice of ``entities.statements`` for the
        well-known ``wikidata:qid`` property, then resolves each entity's
        type via a second query on ``entities.entities``.
        """
        from app.entities.statements import Statement
        from app.entity import Entity

        stmts = Statement.all(where="property_id = 'wikidata:qid' AND value IS NOT NULL AND value <> ''")
        if not stmts:
            return {}

        entity_ids = list({s.entity_id for s in stmts})
        placeholders = ", ".join("?" * len(entity_ids))
        entities = Entity.all(where=f"uuid IN ({placeholders})", params=entity_ids)
        uuid_to_type = {e.uuid: e.type for e in entities}

        groups: dict[str, list[tuple[str, str]]] = {}
        for s in stmts:
            type_name = uuid_to_type.get(s.entity_id)
            if type_name:
                groups.setdefault(type_name, []).append((s.entity_id, s.value))
        return groups

    def _upsert_property(self, pid: str, value_type: str) -> None:
        from app.entities.properties import Property

        existing = Property.find(pid)
        if existing is None:
            Property.from_row((pid, pid, value_type, None, "wikidata", pid, None)).insert()  # ty: ignore[invalid-argument-type]
        else:
            existing.datatype = value_type
            existing.save()

    def _upsert_statement(self, entity_id: str, b: dict[str, Any]) -> None:
        from app.entities.statements import Statement

        statement = Statement.from_row(
            (entity_id, b["pid"], b["value"], b.get("value_label"), b.get("rank", "normal"), None, "wikidata")
        )
        try:
            statement.insert()
        except Exception:
            # Row exists (possibly with SCD2 columns that hide it from find()).
            # Update value_label and rank directly.
            from app.database import cursor

            with cursor() as cur:
                cur.execute(
                    f"UPDATE {Statement._qualified()} SET value_label = ?, rank = ? "
                    "WHERE entity_id = ? AND property_id = ? AND value = ?",
                    [b.get("value_label"), b.get("rank", "normal"), entity_id, b["pid"], b["value"]],
                )


def _pids_for_type(type_name: str) -> list[str]:
    """Return the Wikidata P-ids for properties that belong to this entity type.

    Queries the properties table for properties with source='wikidata'
    and a matching domain_type, returning their wikidata_pid values.
    """
    from app.entities.properties import Property

    properties = Property.all(
        where="source = 'wikidata' AND domain_type = ? AND wikidata_pid IS NOT NULL",
        params=[type_name],
    )
    return [prop.wikidata_pid for prop in properties if prop.wikidata_pid]
