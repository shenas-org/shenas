"""GraphQL schema assembly and FastAPI router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.graphql.mutations import Mutation
from app.graphql.queries import Query

if TYPE_CHECKING:
    from fastapi import Request


async def _get_context(request: Request) -> dict[str, Any]:
    user_id: int = getattr(request.state, "user_id", 0) or 0
    return {"user_id": user_id}


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema, context_getter=_get_context)
