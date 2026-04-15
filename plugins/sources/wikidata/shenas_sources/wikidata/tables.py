"""Wikidata source has no dlt-managed tables.

The Wikidata source populates :class:`app.entities.places.Country` directly
via upserts (see :meth:`WikidataSource.sync`). There are no raw / staging
tables in the ``wikidata.*`` schema -- ``Country`` is the canonical target.

``TABLES`` is kept as an empty tuple so the plugin-discovery machinery in
``app/plugin.py`` and the EntityTable post-sync hook in
``Source._sync_entity_tables`` find a well-formed module.
"""

from __future__ import annotations

TABLES: tuple[type, ...] = ()
