"""GraphQL schema assembly and FastAPI router."""

from __future__ import annotations

from typing import Any

import strawberry
from fastapi import Request
from strawberry.fastapi import GraphQLRouter

from app.graphql.mutations import Mutation
from app.graphql.queries import Query


async def get_context(request: Request) -> dict[str, Any]:
    """Inject request context (user_id) into every GraphQL operation."""
    user_id = getattr(request.state, "user_id", None)
    return {"user_id": user_id if user_id is not None else 0}


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema, context_getter=get_context)
