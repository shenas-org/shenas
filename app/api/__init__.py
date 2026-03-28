"""REST API routers for the shenas server."""

from fastapi import APIRouter

from app.api.config import router as config_router
from app.api.db import router as db_router
from app.api.packages import router as packages_router
from app.api.pipes import router as pipes_router
from app.api.query import router as query_router
from app.api.sync import router as sync_router

api_router = APIRouter(prefix="/api")
api_router.include_router(query_router)
api_router.include_router(config_router)
api_router.include_router(db_router)
api_router.include_router(packages_router)
api_router.include_router(pipes_router)
api_router.include_router(sync_router)
