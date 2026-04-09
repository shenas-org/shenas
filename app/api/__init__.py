"""API routers -- GraphQL + REST endpoints that require non-JSON transports.

Arrow IPC (binary), SSE streaming, and health check remain as REST.
All other data operations are served via GraphQL at /api/graphql.
"""

from fastapi import APIRouter

from app.api.plugins import router as plugins_router
from app.api.query import router as query_router
from app.api.sync import router as sync_router
from app.api.users import router as users_router
from app.graphql import graphql_app

api_router = APIRouter(prefix="/api")
api_router.include_router(query_router)
api_router.include_router(sync_router)
api_router.include_router(plugins_router)
api_router.include_router(users_router)
api_router.include_router(graphql_app, prefix="/graphql")
