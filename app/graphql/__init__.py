"""GraphQL schema assembly and FastAPI router."""

from __future__ import annotations

import strawberry
from fastapi import Request
from strawberry.fastapi import GraphQLRouter

from app.graphql.mutations import Mutation
from app.graphql.queries import Query


async def _context_getter(request: Request) -> dict:
    from app.user_context import get_current_user_id

    return {"request": request, "user_id": get_current_user_id()}


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema, context_getter=_context_getter)
