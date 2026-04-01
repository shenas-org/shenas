"""REST API routers for the shenas server."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.config import router as config_router
from app.api.db import router as db_router
from app.api.plugins import router as plugins_router
from app.api.query import router as query_router
from app.api.sync import router as sync_router
from app.api.models import router as models_router
from app.api.transforms import router as transforms_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(query_router)
api_router.include_router(config_router)
api_router.include_router(db_router)
api_router.include_router(plugins_router)
api_router.include_router(sync_router)
api_router.include_router(transforms_router)
api_router.include_router(models_router)
