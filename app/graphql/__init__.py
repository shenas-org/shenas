"""GraphQL schema assembly and FastAPI router."""

from __future__ import annotations

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.graphql.mutations import Mutation
from app.graphql.queries import Query

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
