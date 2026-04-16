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

import json
import logging
from typing import TYPE_CHECKING, Any

from shenas_sources.core.source import Source

if TYPE_CHECKING:
    from collections.abc import Callable

log = logging.getLogger("shenas.source.wikidata")


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
        from shenas_sources.core.db import connect

        client = self.build_client()
        con = connect()
        total = 0
        try:
            groups = self._load_entity_groups(con)
            if not groups:
                if on_progress:
                    on_progress("statements", "No entities with wikidata:qid found. Set a QID on an entity first.")
                log.info("wikidata sync: no entities with wikidata:qid; nothing to fetch")
                return

            types = {t.name: t for t in EntityType.all()}

            for type_name, pairs in groups.items():
                et = types.get(type_name)
                if et is None:
                    continue
                pids = _pids_for_type(et)
                if not pids:
                    continue
                qids = sorted({qid for _, qid in pairs})
                if on_progress:
                    on_progress(
                        type_name,
                        f"Fetching {len(pids)} properties for {len(qids)} {type_name} entities...",
                    )
                bindings = client.fetch_statements(qids, pids)
                qid_to_entity = {qid: entity_id for entity_id, qid in pairs}
                for b in bindings:
                    entity_id = qid_to_entity.get(b["qid"])
                    if not entity_id:
                        continue
                    self._upsert_property(con, b["pid"], b.get("value_type", "string"))
                    self._upsert_statement(con, entity_id, b)
                    total += 1
        finally:
            client.close()
            con.close()

        if on_progress:
            on_progress("statements", f"Wrote {total} statements from Wikidata.")
        log.info("wikidata sync: wrote %d statements", total)
        self._mark_synced()
        self._log_sync_event(full_refresh)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_entity_groups(self, con: Any) -> dict[str, list[tuple[str, str]]]:
        """Return ``{entity_type: [(entity_id, wikidata_qid), ...]}``.

        Reads the current slice of ``entities.statements`` for the
        well-known ``wikidata:qid`` property and joins with
        ``shenas_system.entities`` to learn each entity's type.
        """
        rows = con.execute(
            """
            SELECT e.type, e.uuid, s.value
            FROM entities.statements s
            JOIN shenas_system.entities e ON e.uuid = s.entity_id
            WHERE s.property_id = 'wikidata:qid'
              AND s._dlt_valid_to IS NULL
              AND s.value IS NOT NULL AND s.value <> ''
            """
        ).fetchall()
        groups: dict[str, list[tuple[str, str]]] = {}
        for type_name, entity_id, qid in rows:
            groups.setdefault(type_name, []).append((entity_id, qid))
        return groups

    def _upsert_property(self, con: Any, pid: str, value_type: str) -> None:
        con.execute(
            "INSERT INTO entities.properties (id, label, datatype, domain_type, source, wikidata_pid) "
            "VALUES (?, ?, ?, NULL, 'wikidata', ?) "
            "ON CONFLICT (id) DO UPDATE SET datatype = excluded.datatype",
            [pid, pid, value_type, pid],
        )

    def _upsert_statement(self, con: Any, entity_id: str, b: dict[str, Any]) -> None:
        con.execute(
            "INSERT INTO entities.statements "
            "(entity_id, property_id, value, value_label, rank, qualifiers, source) "
            "VALUES (?, ?, ?, ?, ?, NULL, 'wikidata') "
            "ON CONFLICT (entity_id, property_id, value) DO UPDATE SET "
            "value_label = excluded.value_label, rank = excluded.rank",
            [entity_id, b["pid"], b["value"], b.get("value_label"), b.get("rank", "normal")],
        )


def _pids_for_type(et: Any) -> list[str]:
    """Return the list of Wikidata P-ids declared on an EntityType."""
    raw = getattr(et, "wikidata_properties", None)
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [p["pid"] for p in parsed if isinstance(p, dict) and p.get("pid")]
