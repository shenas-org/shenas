"""Eurostat source -- city-level demographics and economics from the Urban Audit.

No authentication required. Configure one or more Urban Audit city codes
(e.g. DE004C for Berlin, FR001C for Paris) in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class EurostatSource(Source):
    name = "eurostat"
    display_name = "Eurostat"
    primary_table = "city_population"
    entity_types: ClassVar[list[str]] = ["city"]
    description = (
        "City-level demographics and economics from Eurostat Urban Audit.\n\n"
        "Covers ~900 European cities with population, labour market, GDP, "
        "and living condition indicators. No API key required.\n\n"
        "Set Urban Audit city codes in the Config tab (e.g. DE004C for Berlin)."
    )

    @dataclass
    class Config(SourceConfig):
        city_uuids: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                display_name="Cities",
                description="Select cities to fetch Eurostat data for",
                ui_widget="entity_picker",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.eurostat.client import EurostatClient

        cfg = self.Config.read_row()
        raw_uuids = (cfg or {}).get("city_uuids")
        if not raw_uuids:
            msg = "Select cities in the Config tab."
            raise RuntimeError(msg)
        selected_uuids = [u.strip() for u in raw_uuids.split(",") if u.strip()]
        city_codes = self._resolve_codes_from_uuids(selected_uuids)
        if not city_codes:
            msg = "Selected cities have no Urban Audit codes. Sync Wikidata first to populate city data."
            raise RuntimeError(msg)
        return EurostatClient(city_codes=city_codes)

    def _resolve_codes_from_uuids(self, city_uuids: list[str]) -> list[str]:
        """Extract Urban Audit codes from city entity statements."""
        from app.entities.statements import Statement

        codes = []
        for uuid in city_uuids:
            stmts = Statement.all(
                where="entity_id = ? AND property_id = ?",
                params=[uuid, "eurostat:urban_audit_code"],
                limit=1,
            )
            if stmts:
                codes.append(stmts[0].value)
        return codes

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.eurostat.tables import TABLES

        city_uuid_map = self._resolve_city_uuids(client.city_codes)
        return [t.to_resource(client, city_uuid_map=city_uuid_map) for t in TABLES]

    def _resolve_city_uuids(self, city_codes: list[str]) -> dict[str, str]:
        """Resolve Urban Audit city codes to entity UUIDs.

        Uses the GISCO -> NUTS3 -> Wikidata QID chain to find or create
        city entities, then stores the Urban Audit code as a statement.
        Returns ``{"DE004C": "<uuid>", ...}``.
        """
        from shenas_sources.eurostat.urban_audit import build_urau_to_qid

        mapping = build_urau_to_qid(city_codes)
        result: dict[str, str] = {}

        for urau_code, info in mapping.items():
            qid = info.get("qid")
            city_name = info.get("name", urau_code)
            uuid = self._find_or_create_city(city_name, qid, urau_code)
            if uuid:
                result[urau_code] = uuid

        return result

    def _find_or_create_city(self, name: str, qid: str | None, urau_code: str) -> str | None:
        """Find a city entity by QID, or create one. Store the Urban Audit code."""
        import contextlib

        from app.entities.statements import Statement
        from app.entity import Entity

        # Try to find by Wikidata QID first
        if qid:
            stmts = Statement.all(
                where="property_id = ? AND value = ?",
                params=["wikidata:qid", qid],
                limit=1,
            )
            if stmts:
                entity_uuid = stmts[0].entity_id
                self._ensure_urau_statement(entity_uuid, urau_code)
                return entity_uuid

        # Try to find by name
        entities = Entity.all(where="type = ? AND name = ?", params=["city", name], limit=1)
        if entities:
            self._ensure_urau_statement(entities[0].uuid, urau_code)
            return entities[0].uuid

        # Create new city entity
        entity = Entity(type="city", name=name, status="enabled")
        entity = entity.insert()

        # Store QID statement if we have one
        if qid:
            self._ensure_property("wikidata:qid", "Wikidata QID", "string", source="wikidata")
            with contextlib.suppress(Exception):
                Statement.from_row((entity.uuid, "wikidata:qid", qid, qid, "normal", None, "eurostat")).insert()

        self._ensure_urau_statement(entity.uuid, urau_code)
        return entity.uuid

    def _ensure_urau_statement(self, entity_uuid: str, urau_code: str) -> None:
        """Ensure the eurostat:urban_audit_code statement exists on the entity."""
        import contextlib

        from app.entities.statements import Statement

        self._ensure_property(
            "eurostat:urban_audit_code",
            "Urban Audit Code",
            "string",
            domain_type="city",
            source="eurostat",
        )
        with contextlib.suppress(Exception):
            Statement.from_row(
                (entity_uuid, "eurostat:urban_audit_code", urau_code, urau_code, "normal", None, "eurostat"),
            ).insert()

    @staticmethod
    def _ensure_property(
        prop_id: str,
        label: str,
        datatype: str = "string",
        domain_type: str | None = None,
        source: str = "user",
    ) -> None:
        """Create the property row if it doesn't exist."""
        import contextlib

        from app.entities.properties import Property

        existing = Property.all(where="id = ?", params=[prop_id], limit=1)
        if existing:
            return
        with contextlib.suppress(Exception):
            Property.from_row((prop_id, label, datatype, domain_type, source, None, None)).insert()
