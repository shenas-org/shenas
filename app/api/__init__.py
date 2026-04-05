"""REST API routers -- only endpoints that cannot be served via GraphQL.

Arrow IPC (binary), SSE streaming, and health check remain as REST.
All other data operations have moved to the /graphql endpoint.
"""

from fastapi import APIRouter

from app.api.query import router as query_router
from app.api.sync import router as sync_router

api_router = APIRouter(prefix="/api")
api_router.include_router(query_router)
api_router.include_router(sync_router)
