"""GraphQL schema assembly and FastAPI router.

The schema is composed dynamically from:
1. Core Query/Mutation classes (always present, ``@strawberry.type``)
2. Plugin-contributed mixins discovered via ``shenas.graphql`` entry points

Plugins register a module with ``QueryMixin`` and/or ``MutationMixin``
classes. These are collected at import time and merged into the final
schema via multiple inheritance.
"""

from __future__ import annotations

from typing import Any

import strawberry
from fastapi import Request  # noqa: TC002 - runtime type for context_getter
from strawberry.fastapi import GraphQLRouter

from app.graphql.extensions import _discover_mixins
from app.graphql.mutations import Mutation as CoreMutation
from app.graphql.queries import Query as CoreQuery
from app.graphql.subscriptions import Subscription


async def _get_context(request: Request) -> dict[str, Any]:
    from app.graphql.loaders import create_loaders

    user_id: int = getattr(request.state, "user_id", 0) or 0
    return {"user_id": user_id, **create_loaders()}


def _build_schema() -> strawberry.Schema:
    query_mixins, mutation_mixins = _discover_mixins()

    Query = strawberry.type(type("Query", (*query_mixins, CoreQuery), {})) if query_mixins else CoreQuery
    Mutation = strawberry.type(type("Mutation", (*mutation_mixins, CoreMutation), {})) if mutation_mixins else CoreMutation

    return strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)


schema = _build_schema()
graphql_app = GraphQLRouter(
    schema,
    context_getter=_get_context,
    subscription_protocols=["graphql-transport-ws"],
)
