"""GraphQL schema assembly and FastAPI router."""

from __future__ import annotations

import datetime
import json

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.graphql.mutations import Mutation
from app.graphql.queries import Query


class _JSONEncoder(json.JSONEncoder):
    """Handles datetime/date objects returned by DuckDB in JSON scalar fields."""

    def default(self, o: object) -> object:
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)


class _GraphQLRouter(GraphQLRouter):
    def encode_json(self, data: object) -> str:
        return json.dumps(data, cls=_JSONEncoder)


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = _GraphQLRouter(schema)
