"""Wikidata source -- entity enrichment via the Wikidata Query Service.

No authentication required; the SPARQL endpoint at
https://query.wikidata.org/sparql is public. The source upserts directly
into :class:`app.entities.places.Country` (the canonical place table in
the ``entities`` schema) -- there are no intermediate raw tables in the
``wikidata.*`` schema.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from shenas_sources.core.source import Source

if TYPE_CHECKING:
    from collections.abc import Callable

log = logging.getLogger("shenas.source.wikidata")


class WikidataSource(Source):
    name = "wikidata"
    display_name = "Wikidata"
    # ``<schema>.<table>`` because the rows live in app.entities.places.Country
    # (entities.countries), not in a wikidata.* schema. The Data tab parses
    # this dotted form and routes the table viewer there.
    primary_table = "entities.countries"
    description = (
        "Structured knowledge from Wikidata. Enriches Country entities "
        "(ISO codes, capital, population, area, currency, languages, "
        "coordinates) by querying the Wikidata SPARQL endpoint."
    )

    # Columns on entities.countries that this source owns. Non-wikidata
    # columns (entity_id, name) are identity; wikidata columns are overwritten
    # on every sync. latitude/longitude are only written when SPARQL returned
    # a coordinate, so manual edits survive.
    _WIKIDATA_COLUMNS = (
        "wikidata_qid",
        "description",
        "iso_alpha_2",
        "iso_alpha_3",
        "capital_qid",
        "capital_name",
        "population",
        "area_km2",
        "currency_qid",
        "currency_name",
        "official_languages",
    )

    def build_client(self) -> Any:
        from shenas_sources.wikidata.client import WikidataClient

        return WikidataClient()

    def resources(self, client: Any) -> list[Any]:  # noqa: ARG002
        """No dlt-managed resources -- :meth:`sync` writes straight to Country."""
        return []

    def sync(
        self,
        *,
        full_refresh: bool = False,
        on_progress: Callable[[str, str], None] | None = None,
        **_kwargs: Any,
    ) -> None:
        from app.entities.places import Country
        from app.entity import compute_entity_id

        client = self.build_client()
        if on_progress:
            on_progress("countries", "Fetching countries from Wikidata...")
        try:
            fetched = client.get_countries()
        finally:
            client.close()

        inserted = 0
        updated = 0
        type_name = Country._Meta.entity_type.name
        for row in fetched:
            entity_id = compute_entity_id(type_name, (row["name"],))
            existing = Country.all(where="entity_id = ?", params=[entity_id], limit=1)
            if existing:
                country = existing[0]
                for col in self._WIKIDATA_COLUMNS:
                    setattr(country, col, row.get(col))
                lat, lng = row.get("latitude"), row.get("longitude")
                if lat is not None and lng is not None:
                    country.latitude = lat
                    country.longitude = lng
                country.save()
                updated += 1
            else:
                Country(
                    entity_id=entity_id,
                    name=row["name"],
                    latitude=row.get("latitude") or 0.0,
                    longitude=row.get("longitude") or 0.0,
                    **{c: row.get(c) for c in self._WIKIDATA_COLUMNS},
                ).insert()
                inserted += 1
        if on_progress:
            on_progress("countries", f"Upserted {inserted + updated} countries ({inserted} new, {updated} updated).")
        log.info("wikidata sync: %d inserted, %d updated", inserted, updated)
        self._mark_synced()
        self._log_sync_event(full_refresh)
