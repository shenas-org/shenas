"""Wikidata source has no dlt-managed tables.

The Wikidata source writes statements directly into ``entities.statements``
via :meth:`WikidataSource.sync`. There are no raw / staging tables in a
``wikidata.*`` schema.

``TABLES`` is kept as an empty tuple so the plugin-discovery machinery
finds a well-formed module.
"""

from __future__ import annotations

TABLES: tuple[type, ...] = ()
