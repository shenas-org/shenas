"""Dynamic GraphQL schema composition from plugin contributions.

Plugins contribute query/mutation fields by registering an entry point
in the ``shenas.graphql`` group. Each entry point resolves to a module
that exposes:

- ``QueryMixin`` -- a class with ``@strawberry.field`` methods
- ``MutationMixin`` -- a class with ``@strawberry.mutation`` methods

At startup, :func:`build_schema` discovers all installed extensions,
collects the mixins, and dynamically creates the final ``Query`` and
``Mutation`` classes that inherit from all contributors plus the core.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points

log = logging.getLogger(f"shenas.{__name__}")

_ENTRY_POINT_GROUP = "shenas.graphql"


def _discover_mixins() -> tuple[list[type], list[type]]:
    """Walk installed ``shenas.graphql`` entry points and collect mixins.

    Returns (query_mixins, mutation_mixins).
    """
    query_mixins: list[type] = []
    mutation_mixins: list[type] = []

    for ep in entry_points(group=_ENTRY_POINT_GROUP):
        try:
            module = ep.load()
            if hasattr(module, "QueryMixin"):
                query_mixins.append(module.QueryMixin)
            if hasattr(module, "MutationMixin"):
                mutation_mixins.append(module.MutationMixin)
        except Exception:
            log.warning("Failed to load GraphQL extension '%s'", ep.name, exc_info=True)

    return query_mixins, mutation_mixins
